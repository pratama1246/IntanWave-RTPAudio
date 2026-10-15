import os
import sys
import json
import time
import base64
import socket
import select
import struct
import threading
import subprocess
import shutil
import uuid
import re
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from winotify import Notification, audio

# Refresh Windows Registry PATH
if sys.platform == "win32":
    try:
        import winreg
        paths = []
        for root, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment")
        ]:
            try:
                with winreg.OpenKey(root, subkey) as k:
                    val, _ = winreg.QueryValueEx(k, "Path")
                    paths.append(val)
            except Exception:
                pass
        if paths:
            os.environ["PATH"] = ";".join(paths) + ";" + os.environ.get("PATH", "")
    except Exception:
        pass

# Direktori resources (mendukung PyInstaller bundle)
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    EXE_DIR = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    EXE_DIR = BUNDLE_DIR

CONFIG_FILE = EXE_DIR / "config.json"
if not CONFIG_FILE.exists():
    CONFIG_FILE = BUNDLE_DIR / "config.json"

ICON_PATH = BUNDLE_DIR / "app_icon.png"
if not ICON_PATH.exists():
    ICON_PATH = EXE_DIR / "app_icon.png"


def get_ffplay_bin():
    """Mencari executable ffplay di bundle lokal, direktori aplikasi, atau sistem PATH."""
    candidates = [
        EXE_DIR / "ffplay.exe",
        BUNDLE_DIR / "ffplay.exe",
        EXE_DIR / "_internal" / "ffplay.exe",
        BUNDLE_DIR / "_internal" / "ffplay.exe",
        EXE_DIR / "bin" / "ffplay.exe",
        BUNDLE_DIR / "bin" / "ffplay.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c.resolve())
    w = shutil.which("ffplay")
    if w:
        return w
    return "ffplay"



class AudioReceiver:
    """
    AudioReceiver IntanWave Node:
    1. Siaran Server PA diterima langsung lewat UDP RTP (G.711 A-law 8kHz).
       Meniadakan masalah buffering dan delay pada jaringan WiFi kantor.
    2. Siaran Darurat IP Phone Control Room diterima lewat socket UDP Multicast/Unicast (RTP).
    3. Output dipipa langsung ke ffplay secara non-blocking dengan buffer adaptif.
    """
    PREBUFFER_PACKETS = 4

    def __init__(self, on_status_change=None, on_heartbeat_change=None):
        self.config = self.load_config()
        self.server_url = self.config.get("server_url", "http://10.183.55.114:7080").rstrip("/")
        self.node_id = self.config.get("node_id", "")
        self.device_name = self.config.get("device_name", f"Terminal Audio ({socket.gethostname()})")
        raw_grps = self.config.get("groups") or self.config.get("zone") or ["Kantor"]
        if isinstance(raw_grps, str):
            self.groups = [g.strip() for g in raw_grps.split(",") if g.strip()]
        elif isinstance(raw_grps, list):
            self.groups = [str(g).strip() for g in raw_grps if str(g).strip()]
        else:
            self.groups = ["Kantor"]
        if not self.groups:
            self.groups = ["Kantor"]
        self.zone = ", ".join(self.groups)
        self.multicast_ip = self.config.get("multicast_ip", "239.255.0.1")
        self.multicast_port = int(self.config.get("multicast_port", 5004))
        self.channels = self._init_channels()

        self.status = "STANDBY"  # STANDBY | STREAMING
        self.current_category = "biasa"  # biasa | darurat
        self.current_title = ""
        self.playback_mode = self.config.get("playback_mode", "auto")  # "auto" | "cache" | "stream"
        self.is_running = False
        self.on_status_change = on_status_change
        self.on_heartbeat_change = on_heartbeat_change

        # Telemetri Auto-Discovery / Heartbeat
        self.server_connected = False
        self.registered_ip = ""
        self.registered_groups = list(self.groups)
        self.registered_zone = self.zone
        self.last_heartbeat_time = 0
        self.last_heartbeat_error = ""

        # Pengelolaan Player Audio & State
        self.player_proc = None
        self.player_codec = "alaw"
        self.prebuf = []
        self.prebuf_ready = False
        self.active_source = None  # None | "HTTP" | "RTP"
        self.last_audio_time = 0.0
        self.last_toast_time = 0.0

        # Koneksi Jaringan
        self.stream_sock = None
        self.udp_sockets = []
        self.udp_sock_to_channel = {}
        self.net_sig = []

        # RTP De-duplication (Khusus IP Phone secondary multicast)
        self.seen_seqs = set()
        self.seen_seq_history = []
        self.max_history = 256
        self.active_ssrc = None
        self.active_ssrc_last = 0.0

        # Media & Schedules Sync (Model 1: Cache & Trigger)
        self.media_dir = EXE_DIR / "media"
        try:
            self.media_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.schedules = []
        self.on_schedules_change = None
        self.is_syncing = False
        self.sync_lock = threading.Lock()
        self.active_session_id = None
        self.local_player_proc = None
        self.player_lock = threading.Lock()
        self.last_sync_time = 0.0

        # Background Threads
        self.http_thread = None
        self.udp_thread = None
        self.heartbeat_thread = None
        self.monitor_thread = None

    def _init_channels(self):
        """Membaca daftar channel dari konfigurasi."""
        raw_channels = self.config.get("channels")
        channels = []
        if isinstance(raw_channels, list) and len(raw_channels) > 0:
            for ch in raw_channels:
                if isinstance(ch, dict) and ch.get("ip"):
                    channels.append({
                        "name": ch.get("name", "Channel Audio"),
                        "ip": str(ch.get("ip", "")).strip(),
                        "port": int(ch.get("port", self.multicast_port))
                    })

        has_primary = any(c["ip"] == self.multicast_ip and c["port"] == self.multicast_port for c in channels)
        if not has_primary:
            channels.insert(0, {
                "name": "Server PA Pelindo",
                "ip": self.multicast_ip,
                "port": self.multicast_port
            })

        sec_str = self.config.get("secondary_multicast", "")
        if sec_str and not any("phone" in c["name"].lower() or "control" in c["name"].lower() for c in channels):
            sec_ip = sec_str.split(":")[0].strip()
            sec_port = int(sec_str.split(":")[1].strip()) if ":" in sec_str else self.multicast_port
            if sec_ip:
                channels.append({
                    "name": "Control Room IP Phone",
                    "ip": sec_ip,
                    "port": sec_port
                })

        return channels

    @property
    def secondary_channel_str(self):
        """String pembantu untuk GUI (IP:Port channel kedua/IP Phone)."""
        sec = [c for c in self.channels if c["ip"] != self.multicast_ip or c["port"] != self.multicast_port]
        if sec:
            p = sec[0]["port"]
            return f"{sec[0]['ip']}:{p}" if p != self.multicast_port else sec[0]["ip"]
        return self.config.get("secondary_multicast", "")

    def load_config(self):
        cfg = {}
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
            except Exception:
                pass

        changed = False
        if not cfg.get("server_url"):
            cfg["server_url"] = "http://10.183.55.114:7080"
            changed = True
        clean_host = socket.gethostname().lower().replace(" ", "_").replace("-", "_")
        curr_node_id = cfg.get("node_id", "")
        # Identitas node permanen & stabil per PC (berdasarkan Windows hostname).
        # Tidak menggunakan random UUID agar saat rebuild atau restart, node_id tetap konsisten dan tidak membuat duplikat di server.
        stable_node_id = f"node_{clean_host}"
        if not curr_node_id or curr_node_id == "node_client_01" or not curr_node_id.startswith(f"node_{clean_host}"):
            cfg["node_id"] = stable_node_id
            changed = True
        curr_host = socket.gethostname()
        curr_device_name = cfg.get("device_name", "").strip()
        match_bracket = re.search(r"\(([^)]+)\)", curr_device_name)
        stale_bracket = match_bracket and match_bracket.group(1).strip().upper() != curr_host.strip().upper()
        if not curr_device_name or curr_device_name == "Terminal Audio Node (Amplifier)" or stale_bracket:
            cfg["device_name"] = f"Terminal Audio ({curr_host})"
            changed = True
        if not cfg.get("groups") and not cfg.get("zone"):
            cfg["groups"] = ["Kantor"]
            cfg["zone"] = "Kantor"
            changed = True
        elif cfg.get("groups") and not cfg.get("zone"):
            cfg["zone"] = ", ".join(cfg["groups"])
            changed = True
        if not cfg.get("multicast_ip"):
            cfg["multicast_ip"] = "239.255.0.1"
            changed = True
        if not cfg.get("multicast_port"):
            cfg["multicast_port"] = 5004
            changed = True
        if "channels" not in cfg:
            cfg["channels"] = [
                {
                    "name": "Server PA Pelindo",
                    "ip": cfg.get("multicast_ip", "239.255.0.1"),
                    "port": int(cfg.get("multicast_port", 5004))
                },
                {
                    "name": "Control Room IP Phone",
                    "ip": "239.255.0.2",
                    "port": 5004
                }
            ]
            changed = True
        if "playback_mode" not in cfg:
            cfg["playback_mode"] = "auto"
            changed = True
        if "enable_toast" not in cfg:
            cfg["enable_toast"] = True
            changed = True

        if changed:
            target_path = EXE_DIR / "config.json"
            try:
                with open(target_path, "w") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
        return cfg

    def save_config(self, server_url, device_name, groups_or_zone, ip=None, port=None, secondary_channel="", playback_mode="auto", **kwargs):
        """Menyimpan konfigurasi baru, me-restart listeners, dan mengirim heartbeat pembaruan ke server."""
        self.server_url = server_url.strip().rstrip("/")
        self.device_name = device_name.strip()
        if playback_mode:
            self.playback_mode = playback_mode.strip()
        if isinstance(groups_or_zone, str):
            self.groups = [g.strip() for g in groups_or_zone.split(",") if g.strip()]
        elif isinstance(groups_or_zone, list):
            self.groups = [str(g).strip() for g in groups_or_zone if str(g).strip()]
        else:
            self.groups = ["Kantor"]
        if not self.groups:
            self.groups = ["Kantor"]
        self.zone = ", ".join(self.groups)
        if ip:
            self.multicast_ip = ip.strip()
        if port:
            self.multicast_port = int(port)

        channels = [
            {
                "name": "Server PA Pelindo",
                "ip": self.multicast_ip,
                "port": self.multicast_port
            }
        ]
        sec_clean = secondary_channel.strip() if secondary_channel else ""
        if sec_clean:
            sec_ip = sec_clean.split(":")[0].strip()
            sec_port = int(sec_clean.split(":")[1].strip()) if ":" in sec_clean else self.multicast_port
            if sec_ip:
                channels.append({
                    "name": "Control Room IP Phone",
                    "ip": sec_ip,
                    "port": sec_port
                })
        self.channels = channels

        data = {
            "server_url": self.server_url,
            "node_id": self.node_id,
            "device_name": self.device_name,
            "groups": self.groups,
            "zone": self.zone,
            "multicast_ip": self.multicast_ip,
            "multicast_port": self.multicast_port,
            "channels": self.channels,
            "playback_mode": self.playback_mode,
            "enable_toast": self.config.get("enable_toast", True)
        }
        self.config = data

        target_path = EXE_DIR / "config.json"
        try:
            with open(target_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Gagal menulis config:", e)

        self.stop()
        time.sleep(0.3)
        self.start()

        threading.Thread(target=lambda: self.send_heartbeat(force_update=True), daemon=True).start()

    def send_heartbeat(self, force_update=False):
        """Mengirim heartbeat dan auto-registrasi ke server PA Audio Pelindo."""
        if not self.server_url or not self.node_id:
            return False

        url = f"{self.server_url}/api/nodes/heartbeat"
        payload = {
            "node_id": self.node_id,
            "device_name": self.device_name,
            "groups": self.groups,
            "group": self.zone,
            "zone": self.zone,
            "port": self.multicast_port,
            "hostname": socket.gethostname(),
            "force_update": force_update
        }

        try:
            target_host = self.server_url.split("://")[-1].split(":")[0].split("/")[0]
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((target_host, 80))
            payload["client_ip"] = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                payload["client_ip"] = socket.gethostbyname(socket.gethostname())
            except Exception:
                pass

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "IntanWaveNode/1.0"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    node_data = body.get("node", {})
                    self.server_connected = True
                    self.registered_ip = node_data.get("ip_address") or payload.get("client_ip", "")
                    self.registered_groups = node_data.get("groups") or self.groups
                    self.registered_zone = ", ".join(self.registered_groups) if isinstance(self.registered_groups, list) else (node_data.get("zone") or self.zone)
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_error = ""

                    if self.on_heartbeat_change:
                        self.on_heartbeat_change(True, node_data)
                    if time.time() - self.last_sync_time > 300 or not self.schedules:
                        self.sync_schedules_and_media()
                    return True
        except Exception as e:
            self.server_connected = False
            self.last_heartbeat_error = str(e)
            if self.on_heartbeat_change:
                self.on_heartbeat_change(False, {"error": str(e)})

        return False

    def _heartbeat_loop(self):
        """Loop latar belakang mengirim heartbeat setiap 15 detik."""
        time.sleep(0.5)
        self.send_heartbeat(force_update=False)

        while self.is_running:
            for _ in range(15):
                if not self.is_running:
                    break
                time.sleep(1)

            if self.is_running:
                self.send_heartbeat(force_update=False)

    def notify_toast(self, title, msg):
        """Memunculkan Push Notification Native Windows seketika (non-blocking thread)."""
        if not self.config.get("enable_toast", True):
            return

        now = time.time()
        if now - self.last_toast_time < 2.0:
            return
        self.last_toast_time = now

        def _do_toast():
            try:
                toast_kwargs = {
                    "app_id": "IntanWave Audio System",
                    "title": title,
                    "msg": msg,
                    "duration": "short"
                }
                if ICON_PATH.exists():
                    toast_kwargs["icon"] = str(ICON_PATH.resolve())

                toast = Notification(**toast_kwargs)
                toast.set_audio(audio.Default, loop=False)
                toast.show()
            except Exception as e:
                print("Toast error:", e)

        threading.Thread(target=_do_toast, daemon=True).start()

    def _fetch_playback_info(self):
        """Ambil info status siaran (kategori darurat/biasa & judul) dari server secara asinkron."""
        if not self.server_url:
            return
        try:
            url = f"{self.server_url}/api/playback"
            req = urllib.request.Request(url, headers={"User-Agent": "IntanWaveNode/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    cat = data.get("category") or "biasa"
                    title = data.get("title") or ""
                    if re.search(r"siren|sirine|ews|darurat|emergency|bahaya|evakuasi", title, re.IGNORECASE):
                        cat = "darurat"
                    self.current_category = cat
                    self.current_title = title
                    if self.status == "STREAMING" and self.on_status_change:
                        self.on_status_change("STREAMING", self.current_category, self.current_title)
        except Exception:
            pass

    def set_status(self, new_status, category=None, title=None):
        self.status = new_status
        if category is not None:
            self.current_category = category
        if title is not None:
            self.current_title = title
        if self.on_status_change:
            self.on_status_change(new_status, self.current_category, self.current_title)

    # =========================================================================
    # MODEL 1: CACHE & TRIGGER SCHEDULE SYNC
    # =========================================================================
    def sync_schedules_and_media(self, force=False):
        """
        Sinkronisasi jadwal dan media background untuk node PC ini secara asinkron.
        HANYA mengambil jadwal yang relevan dengan PC ini dari server, dan mengunduh
        file audio yang belum ada di folder media lokal.
        """
        if not self.server_url or not self.node_id:
            return

        def _do_sync():
            if not self.sync_lock.acquire(blocking=False):
                if not force:
                    return
                self.sync_lock.acquire()

            try:
                self.is_syncing = True
                url = f"{self.server_url}/api/nodes/{urllib.parse.quote(self.node_id)}/schedules"
                req = urllib.request.Request(url, headers={"User-Agent": "IntanWaveNode/1.0"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        raw_data = json.loads(resp.read().decode("utf-8"))
                    else:
                        return

                updated_schedules = []
                for item in raw_data:
                    fname = item.get("audio_filename") or item.get("filename") or ""
                    if not fname:
                        item["media_status"] = "Tidak Ada Berkas"
                        updated_schedules.append(item)
                        continue

                    target_file = self.media_dir / fname
                    if not target_file.exists() or target_file.stat().st_size == 0:
                        dl_ok = self._download_media_file(fname)
                        item["media_status"] = "Siap" if dl_ok else "Gagal Unduh"
                    else:
                        item["media_status"] = "Siap"
                    updated_schedules.append(item)

                self.schedules = updated_schedules
                self.last_sync_time = time.time()
                if self.on_schedules_change:
                    self.on_schedules_change(self.schedules)
            except Exception as e:
                print(f"[!] Gagal sinkronisasi jadwal/media: {e}")
            finally:
                self.is_syncing = False
                self.sync_lock.release()

        threading.Thread(target=_do_sync, daemon=True).start()

    def _download_media_file(self, filename: str) -> bool:
        """Mengunduh berkas audio dari server ke direktori media lokal secara aman."""
        if not self.server_url or not filename:
            return False
        dl_url = f"{self.server_url}/api/audio/stream-file/{urllib.parse.quote(filename)}"
        target_path = self.media_dir / filename
        temp_path = self.media_dir / f"{filename}.tmp_{os.getpid()}"
        try:
            req = urllib.request.Request(dl_url, headers={"User-Agent": "IntanWaveNode/1.0"})
            with urllib.request.urlopen(req, timeout=15.0) as resp:
                if resp.status == 200:
                    with open(temp_path, "wb") as f:
                        shutil.copyfileobj(resp, f)
                    if temp_path.exists() and temp_path.stat().st_size > 0:
                        if target_path.exists():
                            try:
                                target_path.unlink()
                            except Exception:
                                pass
                        temp_path.replace(target_path)
                        print(f"[*] Berhasil mengunduh media lokal: {filename} ({target_path.stat().st_size} bytes)")
                        return True
        except Exception as e:
            print(f"[!] Gagal mengunduh file {filename}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
        return False

    def _handle_play_event(self, data: dict):
        """Menangani sinyal trigger siaran audio dari server."""
        session_id = data.get("session_id")
        filename = data.get("filename") or ""
        title = data.get("title") or filename or "Siaran Audio"
        category = data.get("category") or "biasa"

        # Anti dobel request / double click
        with self.player_lock:
            if self.active_session_id and self.active_session_id == session_id:
                return

        threading.Thread(
            target=self._play_local_file_task,
            args=(session_id, filename, title, category),
            daemon=True
        ).start()

    def _play_local_file_task(self, session_id: str, filename: str, title: str, category: str):
        """Memutar berkas media lokal via ffplay ke soundcard amplifier dengan kualitas penuh."""
        if not filename:
            return

        target_file = self.media_dir / filename
        # Jika file belum ada di cache, periksa direktori bundle lokal sebelum mengunduh
        if not target_file.exists() or target_file.stat().st_size == 0:
            alt_local = BUNDLE_DIR / filename
            if not alt_local.exists():
                alt_local = EXE_DIR / filename
            if alt_local.exists() and alt_local.is_file():
                target_file = alt_local
            else:
                self._download_media_file(filename)

        if not target_file.exists():
            print(f"[!] Berkas audio '{filename}' tidak ditemukan di media cache.")
            return

        proc = None
        with self.player_lock:
            self._stop_local_player_locked()
            self._close_player()

            self.active_session_id = session_id
            self.active_source = "LOCAL"
            self.set_status("STREAMING", category, title)
            self.notify_toast("IntanWave — Siaran Audio", f"Memutar: {title}")

            cmd = [
                get_ffplay_bin(),
                "-nodisp",
                "-autoexit",
                "-loglevel", "quiet",
                "-volume", "100",
                str(target_file.resolve())
            ]
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                self.local_player_proc = proc
            except Exception as e:
                print(f"[!] Gagal memutar media lokal {filename}: {e}")
                self._on_local_playback_end(session_id)
                return

        try:
            proc.wait()
        except Exception:
            pass

        self._on_local_playback_end(session_id)

    def _on_local_playback_end(self, session_id: str):
        """Membersihkan state setelah pemutaran audio lokal selesai."""
        with self.player_lock:
            if self.active_session_id != session_id:
                return
            self._stop_local_player_locked()
            self.active_session_id = None
            self.active_source = None
            self.set_status("STANDBY", "biasa", "")
            self._start_player("alaw", 8000)

    def _handle_stop_event(self, data: dict):
        """Menangani perintah stop manual dari server."""
        session_id = data.get("session_id")
        with self.player_lock:
            if session_id and self.active_session_id and session_id != self.active_session_id:
                return
            self._stop_local_player_locked()
            self.active_session_id = None
            self.active_source = None
            self.set_status("STANDBY", "biasa", "")
            self._start_player("alaw", 8000)

    def _stop_local_player_locked(self):
        """Menghentikan proses pemutar file lokal jika sedang aktif."""
        if self.local_player_proc:
            try:
                self.local_player_proc.terminate()
                self.local_player_proc.wait(timeout=0.4)
            except Exception:
                try:
                    self.local_player_proc.kill()
                except Exception:
                    pass
            self.local_player_proc = None

    def _on_stream_end(self):
        """
        Menangani akhir siaran audio secara mulus:
        1. Flush sisa prebuffer jika ada ke player stdin.
        2. Kembalikan status ke STANDBY.
        3. Pastikan audio player tetap pre-warmed dalam mode G.711 A-law 8kHz untuk siaran berikutnya.
        """
        if self.status != "STREAMING" and self.active_source is None:
            return

        if self.player_proc and self.player_proc.stdin and self.player_proc.poll() is None:
            try:
                if self.prebuf:
                    self.player_proc.stdin.write(b"".join(self.prebuf))
                    self.player_proc.stdin.flush()
                # Jika codec PCM/G.711 (misal setelah panggilan IP Phone RTP), tulis padding silence
                if self.player_codec in ("s16le", "alaw", "mulaw"):
                    silence_len = 3528 if self.player_codec == "s16le" else 320
                    silence_val = b"\x00" if self.player_codec != "alaw" else b"\xd5"
                    self.player_proc.stdin.write(silence_val * silence_len)
                    self.player_proc.stdin.flush()
            except Exception:
                pass

        self.prebuf = []
        self.prebuf_ready = False
        self.active_source = None
        self.set_status("STANDBY", "biasa", "")

        # Restart player standby agar fresh dan pre-warmed dalam mode G.711 A-law 8kHz
        self._close_player()
        self._start_player("alaw", 8000)

    def _start_player(self, codec="alaw", sample_rate=8000):
        """Menjalankan ffplay dengan konfigurasi ultra-low latency via pipe stdin."""
        if self.player_proc is not None and self.player_proc.poll() is None:
            if self.player_codec == codec and getattr(self, "player_sample_rate", None) == sample_rate:
                return
            self._close_player()

        if codec == "mp3":
            codec_fmt = "mp3"
            probesize_val = "2048"
        elif codec == "s16le":
            codec_fmt = "s16le"
            probesize_val = "32"
        elif codec == "mulaw":
            codec_fmt = "mulaw"
            probesize_val = "32"
        else:
            codec_fmt = "alaw"
            probesize_val = "32"

        cmd = [
            get_ffplay_bin(),
            "-nodisp",
            "-autoexit",
            "-loglevel", "quiet",
            "-probesize", probesize_val,
            "-analyzeduration", "0",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-volume", "100",
            "-f", codec_fmt,
        ]
        if codec != "mp3":
            sr_str = str(sample_rate or (44100 if codec == "s16le" else 8000))
            cmd.extend([
                "-sample_rate", sr_str,
                "-ch_layout", "mono",
            ])
        cmd.extend(["-i", "-"])

        try:
            self.player_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            self.player_codec = codec
            self.player_sample_rate = sample_rate
            self.prebuf = []
            self.prebuf_ready = False
        except Exception as e:
            print("Gagal menjalankan ffplay player:", e)
            self.player_proc = None

    def _feed_player(self, data: bytes):
        """Menulis chunk audio mentah ke ffplay dengan prebuffer untuk responsivitas instan."""
        if not (self.player_proc and self.player_proc.stdin and self.player_proc.poll() is None):
            self._start_player(self.player_codec or "alaw", getattr(self, "player_sample_rate", 8000) or 8000)
        if not (self.player_proc and self.player_proc.stdin):
            return
        try:
            if not self.prebuf_ready:
                self.prebuf.append(data)
                if len(self.prebuf) >= self.PREBUFFER_PACKETS:
                    self.player_proc.stdin.write(b"".join(self.prebuf))
                    self.player_proc.stdin.flush()
                    self.prebuf = []
                    self.prebuf_ready = True
            else:
                self.player_proc.stdin.write(data)
                self.player_proc.stdin.flush()
        except Exception:
            self._close_player()
            self._start_player(self.player_codec or "alaw", getattr(self, "player_sample_rate", 8000) or 8000)

    def _close_player(self):
        """Menutup proses ffplay dan melepaskan sound card saat aplikasi ditutup atau codec berganti."""
        if self.player_proc and self.prebuf and not self.prebuf_ready:
            try:
                self.player_proc.stdin.write(b"".join(self.prebuf))
                self.player_proc.stdin.flush()
            except Exception:
                pass

        if self.player_proc:
            try:
                if self.player_proc.stdin:
                    self.player_proc.stdin.close()
            except Exception:
                pass
            try:
                self.player_proc.wait(timeout=0.6)
            except Exception:
                try:
                    self.player_proc.kill()
                except Exception:
                    pass
            self.player_proc = None
            self.player_codec = None
            self.player_sample_rate = None

        self.current_category = "biasa"
        self.current_title = ""
        self.prebuf = []
        self.prebuf_ready = False
        self.seen_seqs.clear()
        self.seen_seq_history.clear()
        self.active_ssrc = None
        self.active_ssrc_last = 0.0

    @staticmethod
    def _local_ips():
        """Daftar IP lokal aktif (mendeteksi perubahan DHCP/WiFi)."""
        ips = set()
        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                if not ip.startswith("127."):
                    ips.add(ip)
        except Exception:
            pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return sorted(ips)

    # =========================================================================
    # 1. WEBSOCKET AUDIO STREAM RECEIVER (Persistent RFC 6455 via stdlib socket)
    # =========================================================================
    def _recv_exact(self, sock, n):
        buf = bytearray()
        while len(buf) < n and self.is_running:
            r, _, _ = select.select([sock], [], [], 0.25)
            if not r:
                continue
            try:
                chunk = sock.recv(n - len(buf))
            except Exception:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf) if len(buf) == n else None

    def _ws_stream_loop(self):
        """
        Koneksi WebSocket persistent (RFC 6455) murni stdlib Python (tanpa dependensi eksternal).
        Otomatis menangani frame audio biner, heartbeat ping/pong, dan reconnect instan.
        """
        while self.is_running:
            if not self.server_url or not self.node_id:
                time.sleep(1)
                continue

            try:
                parsed = urllib.parse.urlparse(self.server_url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                path = f"/ws/node/{urllib.parse.quote(self.node_id)}"
            except Exception as e:
                time.sleep(2)
                continue

            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                if sys.platform == "win32" and hasattr(socket, "SIO_KEEPALIVE_VALS"):
                    try:
                        sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 15000, 5000))
                    except Exception:
                        pass
                sock.settimeout(5.0)
                sock.connect((host, port))

                # WebSocket Handshake (RFC 6455)
                sec_key = base64.b64encode(os.urandom(16)).decode("ascii")
                req_lines = [
                    f"GET {path} HTTP/1.1",
                    f"Host: {host}:{port}",
                    "Upgrade: websocket",
                    "Connection: Upgrade",
                    f"Sec-WebSocket-Key: {sec_key}",
                    "Sec-WebSocket-Version: 13",
                    "User-Agent: IntanWaveNode/1.0",
                    "",
                    ""
                ]
                sock.sendall("\r\n".join(req_lines).encode("ascii"))

                # Baca respons handshake
                hdr_buf = b""
                connected_ok = False
                while self.is_running:
                    r, _, _ = select.select([sock], [], [], 1.0)
                    if not r:
                        continue
                    chunk = sock.recv(2048)
                    if not chunk:
                        break
                    hdr_buf += chunk
                    if b"\r\n\r\n" in hdr_buf:
                        if b"101 " in hdr_buf and b"Switching Protocols" in hdr_buf:
                            connected_ok = True
                        break

                if not connected_ok or not self.is_running:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    time.sleep(2.0)
                    continue

                self.stream_sock = sock
                sock.setblocking(False)
                self.server_connected = True
                print(f"[*] IntanWave Node tersambung via WebSocket Audio Stream ({self.server_url})")

                last_ping_time = time.time()

                # Loop membaca frame WebSocket
                while self.is_running:
                    now = time.time()
                    if now - last_ping_time > 20.0:
                        last_ping_time = now
                        try:
                            ping_payload = b"ping"
                            mask = os.urandom(4)
                            frame_hdr = bytearray([0x81, 0x80 | len(ping_payload)])
                            frame_hdr.extend(mask)
                            frame_hdr.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(ping_payload)))
                            sock.sendall(frame_hdr)
                        except Exception:
                            break

                    r, _, _ = select.select([sock], [], [], 0.25)
                    if not r:
                        continue

                    hdr = self._recv_exact(sock, 2)
                    if not hdr:
                        break
                    b0, b1 = hdr[0], hdr[1]
                    opcode = b0 & 0x0F
                    masked = (b1 & 0x80) != 0
                    length = b1 & 0x7F

                    if length == 126:
                        ext = self._recv_exact(sock, 2)
                        if not ext: break
                        length = struct.unpack("!H", ext)[0]
                    elif length == 127:
                        ext = self._recv_exact(sock, 8)
                        if not ext: break
                        length = struct.unpack("!Q", ext)[0]

                    mask_key = None
                    if masked:
                        mask_key = self._recv_exact(sock, 4)
                        if not mask_key: break

                    payload = self._recv_exact(sock, length) if length > 0 else b""
                    if payload is None:
                        break
                    if masked and mask_key:
                        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

                    # Opcode 0x1: Pesan Teks (Kontrol / Event JSON / stream_end)
                    if opcode == 0x1:
                        try:
                            text_msg = payload.decode("utf-8", errors="ignore").strip()
                            if text_msg.startswith("{"):
                                data = json.loads(text_msg)
                                action = data.get("action")
                                msg_type = data.get("type")
                                if action == "play":
                                    if self.playback_mode == "stream":
                                        pass
                                    elif self.playback_mode == "cache":
                                        self._handle_play_event(data)
                                    else:
                                        self._handle_play_event(data)
                                elif action == "stop":
                                    self._handle_stop_event(data)
                                    if self.active_source == "WS":
                                        self._on_stream_end()
                                elif msg_type in ("schedules_update", "audio_update"):
                                    self.sync_schedules_and_media(force=True)
                                elif msg_type == "stream_end":
                                    if self.active_source == "WS":
                                        self._on_stream_end()
                            elif "stream_end" in text_msg:
                                if self.active_source == "WS":
                                    self._on_stream_end()
                        except Exception:
                            pass

                    # Opcode 0x2: Biner Audio Frame
                    elif opcode == 0x2:
                        if self.active_source == "LOCAL":
                            continue

                        if self.playback_mode == "cache":
                            continue

                        now_audio = time.time()
                        if self.active_source == "RTP" and (now_audio - self.last_audio_time < 2.5):
                            continue

                        if self.active_source != "WS":
                            self.active_source = "WS"
                            self.set_status("STREAMING", "biasa", "Siaran Server PA (Stream Live)")
                            self.notify_toast("IntanWave — Siaran Server (Live Stream)", f"Menerima streaming audio langsung dari {self.server_url}")
                            threading.Thread(target=self._fetch_playback_info, daemon=True).start()
                            self._start_player("mp3", 44100)

                        self.last_audio_time = now_audio
                        self._feed_player(payload)

                    # Opcode 0x9: Ping dari server -> balas Pong (Opcode 0xA)
                    elif opcode == 0x9:
                        try:
                            mask = os.urandom(4)
                            pong_hdr = bytearray([0x8A, 0x80 | len(payload)])
                            pong_hdr.extend(mask)
                            pong_hdr.extend(bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
                            sock.sendall(pong_hdr)
                        except Exception:
                            break

                    # Opcode 0x8: Close
                    elif opcode == 0x8:
                        break

            except Exception:
                pass
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                if self.stream_sock == sock:
                    self.stream_sock = None

            if self.is_running:
                if self.active_source == "WS":
                    self._on_stream_end()
                time.sleep(1.5)

    # =========================================================================
    # 2. UDP MULTICAST / UNICAST RECEIVER (Server PA & Control Room IP Phone)
    # =========================================================================
    def _bind_udp_sockets(self):
        """Bind socket UDP multicast dan unicast untuk Server PA dan IP Phone."""
        for s in self.udp_sockets:
            try:
                s.close()
            except Exception:
                pass
        self.udp_sockets.clear()
        self.udp_sock_to_channel.clear()

        if not self.channels:
            return True

        self.net_sig = self._local_ips()
        port_map = {}
        for ch in self.channels:
            p = int(ch.get("port", self.multicast_port))
            port_map.setdefault(p, []).append(ch)

        for p, ch_list in port_map.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262144)
                except Exception:
                    pass
                sock.bind(("", p))

                for ch in ch_list:
                    ch_ip = ch.get("ip", "").strip()
                    try:
                        first_oct = int(ch_ip.split(".")[0])
                        is_mc = (224 <= first_oct <= 239)
                    except Exception:
                        is_mc = False
                    if not is_mc:
                        continue

                    try:
                        mreq = struct.pack("4sl", socket.inet_aton(ch_ip), socket.INADDR_ANY)
                        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                    except Exception as e:
                        print(f"Warning: gagal join multicast {ch_ip}:", e)

                    for iface_ip in self.net_sig:
                        try:
                            mreq_if = struct.pack("4s4s", socket.inet_aton(ch_ip), socket.inet_aton(iface_ip))
                            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq_if)
                        except Exception:
                            pass

                sock.setblocking(False)
                self.udp_sockets.append(sock)
                self.udp_sock_to_channel[sock] = ch_list
            except Exception as e:
                print(f"Gagal bind UDP socket port {p}: {e}")

        return True

    def _handle_udp_packet(self, sock, data, addr):
        """Memproses paket RTP dari UDP Unicast / Multicast (Server PA & IP Phone)."""
        if len(data) < 12:
            return
        now = time.time()

        b0 = data[0]
        cc = b0 & 0x0F
        x_bit = (b0 >> 4) & 0x01
        pt = data[1] & 0x7F
        seq_num = struct.unpack("!H", data[2:4])[0]
        ssrc = struct.unpack("!I", data[8:12])[0]

        # Kunci SSRC & deduplikasi
        if self.active_ssrc is None or (now - self.active_ssrc_last) > 0.4:
            if self.active_ssrc is not None and ssrc != self.active_ssrc:
                self.seen_seqs.clear()
                self.seen_seq_history.clear()
            self.active_ssrc = ssrc
        elif ssrc != self.active_ssrc:
            return
        self.active_ssrc_last = now

        if seq_num in self.seen_seqs:
            return
        self.seen_seqs.add(seq_num)
        self.seen_seq_history.append(seq_num)
        if len(self.seen_seq_history) > self.max_history:
            self.seen_seqs.discard(self.seen_seq_history.pop(0))

        offset = 12 + (cc * 4)
        if x_bit and len(data) >= offset + 4:
            ext_len = struct.unpack("!H", data[offset + 2:offset + 4])[0]
            offset += 4 + (ext_len * 4)
        payload = data[offset:] if len(data) > offset else None
        if not payload:
            return

        server_host = ""
        if self.server_url:
            try:
                server_host = urllib.parse.urlparse(self.server_url).hostname or ""
            except Exception:
                pass

        is_server = (addr[0] == server_host) or (addr[0] == self.multicast_ip)
        source_key = "RTP_SERVER" if is_server else "RTP_PHONE"

        if self.active_source != source_key:
            if self.active_source == "LOCAL":
                with self.player_lock:
                    self._stop_local_player_locked()
                    self.active_session_id = None
            self.active_source = source_key
            if is_server:
                self.set_status("STREAMING", "biasa", "Siaran Server PA (UDP)")
                self.notify_toast("IntanWave — Siaran Server UDP", "Menerima siaran audio UDP dari Server PA")
                threading.Thread(target=self._fetch_playback_info, daemon=True).start()
                codec = "alaw"
            else:
                ch_list = self.udp_sock_to_channel.get(sock, [])
                ch_name = ch_list[0]["name"] if ch_list else "Control Room IP Phone"
                self.set_status("STREAMING", "darurat", ch_name)
                self.notify_toast(f"IntanWave — {ch_name}", f"Menerima panggilan siaran dari {addr[0]}")
                codec = "mulaw" if pt == 0 else "alaw"

            self._start_player(codec, 8000)

        self.last_audio_time = now
        self._feed_player(payload)

    def _udp_rtp_loop(self):
        """Loop penerima RTP UDP untuk channel sekunder (IP Phone)."""
        self._bind_udp_sockets()
        last_net_check = time.time()

        while self.is_running:
            try:
                # Deteksi perubahan interface jaringan tiap 5 detik
                if time.time() - last_net_check > 5.0:
                    last_net_check = time.time()
                    if self._local_ips() != self.net_sig:
                        self._bind_udp_sockets()

                if not self.udp_sockets:
                    time.sleep(0.5)
                    continue

                readable, _, _ = select.select(self.udp_sockets, [], [], 0.25)
                for sock in readable:
                    try:
                        data, addr = sock.recvfrom(2048)
                    except Exception:
                        continue
                    self._handle_udp_packet(sock, data, addr)

            except Exception:
                time.sleep(0.05)

    # =========================================================================
    # 3. MONITOR LOOP (Deteksi Berhentinya Siaran & Idle Cleanup)
    # =========================================================================
    def _monitor_loop(self):
        """Memantau selesainya siaran jika tidak ada paket/chunk audio selama > 1.5 detik (toleransi jitter WiFi)."""
        while self.is_running:
            time.sleep(0.1)
            if self.status == "STREAMING":
                if time.time() - self.last_audio_time > 1.5:
                    self._on_stream_end()

    # =========================================================================
    # LIFECYCLE MANAGEMENT (Start, Stop, Test Audio)
    # =========================================================================
    def start(self):
        if self.is_running:
            return
        self.is_running = True

        # Pre-warm / Hot-Standby Audio Player
        # Membuka ffplay ke Windows Audio Engine (WASAPI) sejak awal agar tidak ada delay cold-start
        self._start_player("alaw", 8000)

        self.stream_thread = threading.Thread(target=self._ws_stream_loop, daemon=True)
        self.stream_thread.start()

        self.udp_thread = threading.Thread(target=self._udp_rtp_loop, daemon=True)
        self.udp_thread.start()

        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.is_running = False
        with self.player_lock:
            self._stop_local_player_locked()
            self.active_session_id = None
        self._on_stream_end()
        self._close_player()

        if self.stream_sock:
            try:
                self.stream_sock.close()
            except Exception:
                pass
            self.stream_sock = None

        for s in self.udp_sockets:
            try:
                s.close()
            except Exception:
                pass
        self.udp_sockets.clear()
        self.udp_sock_to_channel.clear()

    def play_test_chime(self):
        """Memutar nada bel uji coba langsung ke soundcard Windows / amplifier."""
        self.notify_toast(
            "IntanWave — Uji Coba Audio",
            "Memutar nada bel ding-dong ke speaker terminal."
        )

        def _play_audio():
            candidates = [
                EXE_DIR / "test_chime.wav",
                BUNDLE_DIR / "test_chime.wav",
                EXE_DIR / "_internal" / "test_chime.wav",
                BUNDLE_DIR / "_internal" / "test_chime.wav",
            ]
            for candidate in candidates:
                if candidate.exists():
                    sound_path = str(candidate.resolve())
                    if sys.platform == "win32":
                        try:
                            import winsound
                            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            return
                        except Exception as e:
                            print("Winsound error:", e)

                    try:
                        ffplay_bin = get_ffplay_bin()
                        subprocess.run(
                            [ffplay_bin, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", "100", sound_path],
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                            timeout=5
                        )
                        return
                    except Exception as e:
                        print("FFplay chime error:", e)

            if sys.platform == "win32":
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        threading.Thread(target=_play_audio, daemon=True).start()
        return True
