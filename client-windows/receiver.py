import os
import sys
import json
import time
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
    1. Siaran Server PA diterima langsung lewat HTTP Stream per IP/node_id (ultra-low latency G.711 A-law 8kHz).
       Meniadakan masalah duplikasi audio, paket hilang, atau rebinding multicast pada jaringan WiFi & DHCP.
    2. Siaran Darurat IP Phone Control Room tetap diterima lewat socket UDP Multicast sekunder (RTP).
    3. Output dipipa langsung ke ffplay secara non-blocking dengan buffer adaptif ~120ms (tahan jitter WiFi).
    """
    PREBUFFER_PACKETS = 6  # 6 paket x 20ms = ~120ms initial prebuffer (latensi ultra-rendah & tahan jitter)

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
        if not cfg.get("node_id") or cfg.get("node_id") == "node_client_01":
            clean_host = socket.gethostname().lower().replace(" ", "_").replace("-", "_")
            cfg["node_id"] = f"node_{clean_host}_{uuid.uuid4().hex[:6]}"
            changed = True
        if not cfg.get("device_name"):
            cfg["device_name"] = f"Terminal Audio ({socket.gethostname()})"
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
        if "enable_toast" not in cfg:
            cfg["enable_toast"] = True
            changed = True
        if "volume" not in cfg:
            cfg["volume"] = 100
            changed = True

        if changed:
            target_path = EXE_DIR / "config.json"
            try:
                with open(target_path, "w") as f:
                    json.dump(cfg, f, indent=2)
            except Exception:
                pass
        return cfg

    def save_config(self, server_url, device_name, groups_or_zone, ip, port, secondary_channel=""):
        """Menyimpan konfigurasi baru, me-restart listeners, dan mengirim heartbeat pembaruan ke server."""
        self.server_url = server_url.strip().rstrip("/")
        self.device_name = device_name.strip()
        if isinstance(groups_or_zone, str):
            self.groups = [g.strip() for g in groups_or_zone.split(",") if g.strip()]
        elif isinstance(groups_or_zone, list):
            self.groups = [str(g).strip() for g in groups_or_zone if str(g).strip()]
        else:
            self.groups = ["Kantor"]
        if not self.groups:
            self.groups = ["Kantor"]
        self.zone = ", ".join(self.groups)
        self.multicast_ip = ip.strip()
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
            "enable_toast": self.config.get("enable_toast", True),
            "volume": self.config.get("volume", 100)
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

    def _start_player(self, codec="alaw"):
        """Menjalankan ffplay dengan konfigurasi ultra-low latency via pipe stdin."""
        if self.player_proc is not None and self.player_proc.poll() is None:
            if self.player_codec == codec:
                return
            self._close_player()

        vol = max(0, min(100, int(self.config.get("volume", 100))))
        codec_fmt = "mulaw" if codec == "mulaw" else "alaw"
        cmd = [
            get_ffplay_bin(),
            "-nodisp",
            "-autoexit",
            "-loglevel", "quiet",
            "-probesize", "32",
            "-analyzeduration", "0",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-volume", str(vol),
            "-f", codec_fmt,
            "-sample_rate", "8000",
            "-ch_layout", "mono",
            "-i", "-"
        ]
        try:
            self.player_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            self.player_codec = codec
            self.prebuf = []
            self.prebuf_ready = False
        except Exception as e:
            print("Gagal menjalankan ffplay player:", e)
            self.player_proc = None

    def _feed_player(self, data: bytes):
        """Menulis chunk audio mentah ke ffplay dengan prebuffer kecil (~120ms) untuk mencegah jitter WiFi."""
        if not (self.player_proc and self.player_proc.stdin):
            return
        try:
            if self.player_proc.poll() is not None:
                self._close_player()
                return

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

    def _close_player(self):
        """Menutup proses ffplay dan melepaskan sound card saat siaran selesai."""
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
    # 1. HTTP STREAM RECEIVER (Siaran Server PA Langsung via TCP/HTTP Stream)
    # =========================================================================
    def _read_http_chunk(self, sock, cur_buf, timeout=0.25):
        """
        Membaca 1 HTTP chunked frame secara non-blocking via select.select.
        Mengembalikan (chunk_bytes, sisa_buffer, is_alive).
        """
        while self.is_running:
            if b"\r\n" not in cur_buf:
                r, _, _ = select.select([sock], [], [], timeout)
                if not r:
                    return None, cur_buf, True
                try:
                    data = sock.recv(4096)
                except Exception:
                    return None, cur_buf, False
                if not data:
                    return None, cur_buf, False
                cur_buf += data
                continue

            line, rest = cur_buf.split(b"\r\n", 1)
            line = line.strip()
            if not line:
                cur_buf = rest
                continue

            # Parsing panjang chunk (heksadesimal)
            try:
                chunk_len = int(line.split(b";")[0], 16)
            except ValueError:
                return None, b"", False

            if chunk_len == 0:
                return None, rest, False  # Akhir stream chunked

            # Pastikan seluruh chunk + \r\n penutup sudah terbaca
            while len(rest) < chunk_len + 2 and self.is_running:
                r, _, _ = select.select([sock], [], [], timeout)
                if not r:
                    return None, rest, True
                try:
                    data = sock.recv(4096)
                except Exception:
                    return None, rest, False
                if not data:
                    return None, rest, False
                rest += data

            chunk_data = rest[:chunk_len]
            cur_buf = rest[chunk_len + 2:]
            return chunk_data, cur_buf, True

        return None, cur_buf, False

    def _http_stream_loop(self):
        """
        Koneksi HTTP persistent ke {server_url}/api/stream?node_id={node_id}.
        Data audio dialirkan langsung saat ada siaran server tanpa perlu RTP/multicast.
        """
        while self.is_running:
            if not self.server_url or not self.node_id:
                time.sleep(1)
                continue

            # Parse host & port dari server_url
            try:
                parsed = urllib.parse.urlparse(self.server_url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                path = f"/api/stream?node_id={urllib.parse.quote(self.node_id)}"
            except Exception as e:
                print(f"[HTTP Stream] Format URL salah ({self.server_url}):", e)
                time.sleep(2)
                continue

            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((host, port))
                sock.setblocking(False)

                # Kirim HTTP Request
                req_lines = [
                    f"GET {path} HTTP/1.1",
                    f"Host: {host}:{port}",
                    "User-Agent: IntanWaveNode/1.0",
                    "Accept: application/octet-stream",
                    "Connection: keep-alive",
                    "",
                    ""
                ]
                req_raw = "\r\n".join(req_lines).encode("ascii")
                sock.sendall(req_raw)

                # Baca Header Respons HTTP
                hdr_buf = b""
                connected_ok = False
                while self.is_running:
                    r, _, _ = select.select([sock], [], [], 0.5)
                    if not r:
                        continue
                    chunk = sock.recv(2048)
                    if not chunk:
                        break
                    hdr_buf += chunk
                    if b"\r\n\r\n" in hdr_buf:
                        connected_ok = True
                        break

                if not connected_ok or not self.is_running:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    time.sleep(1.5)
                    continue

                parts = hdr_buf.split(b"\r\n\r\n", 1)
                status_line = parts[0].split(b"\r\n")[0].decode("ascii", errors="replace")
                if " 200 " not in status_line:
                    print(f"[HTTP Stream] Server merespons {status_line}, mencoba ulang...")
                    try:
                        sock.close()
                    except Exception:
                        pass
                    time.sleep(2.0)
                    continue

                self.stream_sock = sock
                cur_buf = parts[1] if len(parts) > 1 else b""
                print(f"[*] IntanWave Node tersambung ke HTTP Audio Stream ({self.server_url})")

                # Loop penerimaan audio
                while self.is_running:
                    audio_chunk, cur_buf, ok = self._read_http_chunk(sock, cur_buf, timeout=0.25)
                    if not ok:
                        break

                    if not audio_chunk:
                        continue

                    now = time.time()
                    # Jika ada panggilan RTP dari IP Phone yang sedang aktif, biarkan IP Phone
                    if self.active_source == "RTP" and (now - self.last_audio_time < 0.8):
                        continue

                    # Mulai pemutaran jika belum aktif
                    if self.active_source != "HTTP":
                        self.active_source = "HTTP"
                        self.set_status("STREAMING", "biasa", "Siaran Server PA")
                        self.notify_toast("IntanWave — Siaran Server", f"Menerima siaran audio dari {self.server_url}")
                        threading.Thread(target=self._fetch_playback_info, daemon=True).start()
                        self._start_player("alaw")

                    self.last_audio_time = now
                    self._feed_player(audio_chunk)

            except Exception as e:
                # Menangani putus koneksi jaringan/reboot server
                pass
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                self.stream_sock = None

            if self.is_running:
                if self.active_source == "HTTP":
                    self._close_player()
                    self.active_source = None
                    self.set_status("STANDBY", "biasa", "")
                time.sleep(1.5)

    # =========================================================================
    # 2. UDP MULTICAST RECEIVER (Khusus Secondary / Control Room IP Phone)
    # =========================================================================
    def _bind_udp_sockets(self):
        """Bind socket UDP multicast hanya untuk channel sekunder (misal Control Room IP Phone)."""
        for s in self.udp_sockets:
            try:
                s.close()
            except Exception:
                pass
        self.udp_sockets.clear()
        self.udp_sock_to_channel.clear()

        # Identifikasi channel sekunder (bukan server primary yang sudah ditangani via HTTP)
        sec_channels = [
            c for c in self.channels
            if ("phone" in c.get("name", "").lower() or "control" in c.get("name", "").lower()
                or c.get("ip") != self.multicast_ip)
        ]

        if not sec_channels:
            return True

        self.net_sig = self._local_ips()
        port_map = {}
        for ch in sec_channels:
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
                        print(f"Warning: gagal join multicast secondary {ch_ip}:", e)

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
                print(f"Gagal bind secondary UDP socket port {p} ({e})")

        return True

    def _handle_udp_packet(self, sock, data, addr):
        """Memproses paket RTP dari channel sekunder (IP Phone)."""
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

        # Jika siaran server PA via HTTP sedang aktif, IP Phone diabaikan agar tidak tumpang tindih
        if self.active_source == "HTTP" and (now - self.last_audio_time < 0.8):
            return

        if self.active_source != "RTP":
            self.active_source = "RTP"
            ch_list = self.udp_sock_to_channel.get(sock, [])
            ch_name = ch_list[0]["name"] if ch_list else "Control Room IP Phone"
            self.set_status("STREAMING", "darurat", ch_name)
            self.notify_toast(f"IntanWave — {ch_name}", f"Menerima panggilan siaran dari {addr[0]}")
            codec = "mulaw" if pt == 0 else "alaw"
            self._start_player(codec)

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
        """Memantau selesainya siaran jika tidak ada paket/chunk audio selama > 0.8 detik."""
        while self.is_running:
            time.sleep(0.1)
            if self.status == "STREAMING":
                if time.time() - self.last_audio_time > 0.8:
                    self._close_player()
                    self.active_source = None
                    self.set_status("STANDBY", "biasa", "")

    # =========================================================================
    # LIFECYCLE MANAGEMENT (Start, Stop, Test Audio)
    # =========================================================================
    def start(self):
        if self.is_running:
            return
        self.is_running = True

        self.http_thread = threading.Thread(target=self._http_stream_loop, daemon=True)
        self.http_thread.start()

        self.udp_thread = threading.Thread(target=self._udp_rtp_loop, daemon=True)
        self.udp_thread.start()

        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.is_running = False
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
                        vol = int(self.config.get("volume", 100))
                        vol = max(0, min(100, vol))
                        subprocess.run(
                            [ffplay_bin, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(vol), sound_path],
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
