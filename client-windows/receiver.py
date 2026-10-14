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
    PREBUFFER_PACKETS = 8  # 8 paket x 20ms = ~160ms jitter buffer awal (tahan jitter WiFi)

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

        self.player_proc = None
        self.last_packet_time = 0
        self.sock = None
        self.sockets = []
        self.sock_to_channels = {}
        self.thread = None
        self.heartbeat_thread = None
        self.last_toast_time = 0
        
        # RTP Sequence Number Deduplication (Mencegah gema/suara dobel)
        self.seen_seqs = set()
        self.seen_seq_history = []
        self.max_history = 512

        # Anti audio dobel: kunci satu sumber (SSRC) + jitter prebuffer + deteksi perubahan jaringan
        self.active_ssrc = None
        self.active_ssrc_last = 0.0
        self.prebuf = []
        self.prebuf_ready = False
        self.net_sig = []

    def _init_channels(self):
        """Membaca daftar channel RTP dari konfigurasi atau membuat default (Server + IP Phone)."""
        raw_channels = self.config.get("channels")
        channels = []
        if isinstance(raw_channels, list) and len(raw_channels) > 0:
            for ch in raw_channels:
                if isinstance(ch, dict) and ch.get("ip"):
                    channels.append({
                        "name": ch.get("name", "Channel RTP"),
                        "ip": str(ch.get("ip", "")).strip(),
                        "port": int(ch.get("port", self.multicast_port))
                    })
        
        # Pastikan channel primary selalu terdaftar
        has_primary = any(c["ip"] == self.multicast_ip and c["port"] == self.multicast_port for c in channels)
        if not has_primary:
            channels.insert(0, {
                "name": "Server IntanWave",
                "ip": self.multicast_ip,
                "port": self.multicast_port
            })

        # Pastikan ada channel secondary jika ada di config (misal IP Phone)
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
                    "name": "Server IntanWave",
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
        """Menyimpan konfigurasi baru, me-restart socket receiver, dan mengirim heartbeat pembaruan ke server."""
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
            
        # Update daftar channels
        channels = [
            {
                "name": "Server IntanWave",
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
        
        # Simpan ke config.json di sebelah file .exe
        target_path = EXE_DIR / "config.json"
        try:
            with open(target_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Gagal menulis config:", e)

        # Restart listener dengan IP/port baru
        self.stop()
        time.sleep(0.3)
        self.start()

        # Kirim sinyal heartbeat pembaruan seketika ke server (force_update=True)
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

        # Deteksi local interface IP yang mengarah ke server
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
        # Kirim pertama kali langsung setelah start
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

        # Jalankan di background thread agar instan tanpa nunggu/block audio
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
                    # Fallback heuristik jika judul mengandung kata darurat
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

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def stop(self):
        self.is_running = False
        self._close_player()
        for s in self.sockets:
            try:
                s.close()
            except Exception:
                pass
        self.sockets.clear()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _close_player(self):
        # Flush sisa prebuffer (siaran sangat pendek) sebelum menutup player
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
                self.player_proc.wait(timeout=1.2)
            except Exception:
                try:
                    self.player_proc.kill()
                except Exception:
                    pass
            self.player_proc = None
        self.current_category = "biasa"
        self.current_title = ""
        self.seen_seqs.clear()
        self.seen_seq_history.clear()
        self.active_ssrc = None
        self.active_ssrc_last = 0.0
        self.prebuf = []
        self.prebuf_ready = False

    @staticmethod
    def _local_ips():
        """Daftar IP lokal non-loopback (dipakai mendeteksi perubahan jaringan: DHCP / WiFi roaming)."""
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

    def _bind_sockets(self):
        """Bind socket per port UDP & join grup multicast di semua adapter aktif. Return True jika ada socket aktif."""
        for s in self.sockets:
            try:
                s.close()
            except Exception:
                pass
        self.sockets.clear()
        self.sock_to_channels.clear()
        self.sock = None

        self.net_sig = self._local_ips()

        port_map = {}
        for ch in self.channels:
            p = int(ch.get("port", self.multicast_port))
            port_map.setdefault(p, []).append(ch)

        for p, ch_list in port_map.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Buffer terima besar agar tahan burst/jitter WiFi
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
                        print(f"Warning: gagal join multicast default {ch_ip}:", e)

                    for iface_ip in self.net_sig:
                        try:
                            mreq_if = struct.pack("4s4s", socket.inet_aton(ch_ip), socket.inet_aton(iface_ip))
                            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq_if)
                        except Exception:
                            pass  # sudah tergabung / adapter tidak mendukung

                sock.setblocking(False)
                self.sockets.append(sock)
                self.sock_to_channels[sock] = ch_list
            except Exception as e:
                print(f"Gagal bind socket port {p} ({e})")

        if self.sockets:
            self.sock = self.sockets[0]
            ch_info = ", ".join([f"{c['name']} (rtp://{c['ip']}:{c['port']})" for c in self.channels])
            print(f"[*] IntanWave Node standby, {len(self.channels)} channel RTP: {ch_info} | NIC: {self.net_sig}")
            return True
        return False

    def _start_player(self, pt):
        vol = max(0, min(100, int(self.config.get("volume", 100))))
        # pt=0 -> PCMU (mulaw), selain itu PCMA (alaw)
        codec_fmt = "mulaw" if pt == 0 else "alaw"
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
        self.player_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        )
        self.prebuf = []
        self.prebuf_ready = False

    def _handle_packet(self, sock, data, addr):
        if len(data) < 12:
            return
        now = time.time()

        b0 = data[0]
        cc = b0 & 0x0F
        x_bit = (b0 >> 4) & 0x01
        pt = data[1] & 0x7F
        seq_num = struct.unpack("!H", data[2:4])[0]
        ssrc = struct.unpack("!I", data[8:12])[0]

        # --- Anti audio dobel #1: kunci ke SATU sumber (SSRC) selama siaran berlangsung ---
        # Unicast + multicast dari server (atau IP Phone + server) punya SSRC berbeda -> yang kedua diabaikan.
        # Kunci dilepas jika sumber terkunci diam > 0.4 detik (failover otomatis / pergantian lagu).
        if self.active_ssrc is None or (now - self.active_ssrc_last) > 0.4:
            if self.active_ssrc is not None and ssrc != self.active_ssrc:
                self.seen_seqs.clear()
                self.seen_seq_history.clear()
            self.active_ssrc = ssrc
        elif ssrc != self.active_ssrc:
            return
        self.active_ssrc_last = now

        # --- Anti audio dobel #2: buang paket duplikat (SSRC & seq sama via unicast + multicast / multi-NIC) ---
        if seq_num in self.seen_seqs:
            return
        self.seen_seqs.add(seq_num)
        self.seen_seq_history.append(seq_num)
        if len(self.seen_seq_history) > self.max_history:
            self.seen_seqs.discard(self.seen_seq_history.pop(0))

        self.last_packet_time = now

        offset = 12 + (cc * 4)
        if x_bit and len(data) >= offset + 4:
            ext_len = struct.unpack("!H", data[offset + 2:offset + 4])[0]
            offset += 4 + (ext_len * 4)
        payload = data[offset:] if len(data) > offset else None
        if not payload:
            return

        if self.player_proc is None:
            ch_list = self.sock_to_channels.get(sock, [])
            ch_name = ch_list[0]["name"] if ch_list else "Siaran Audio"
            is_ip_phone = ("phone" in ch_name.lower()) or ("control" in ch_name.lower())
            cat = "darurat" if is_ip_phone else "biasa"
            title = ch_name if is_ip_phone else f"Siaran Masuk ({ch_name})"

            self.notify_toast(f"IntanWave — {ch_name}", f"Menerima panggilan siaran dari {addr[0]}")
            self.set_status("STREAMING", cat, title)
            if not is_ip_phone:
                threading.Thread(target=self._fetch_playback_info, daemon=True).start()
            self._start_player(pt)

        if not (self.player_proc and self.player_proc.stdin):
            return
        try:
            if self.player_proc.poll() is not None:
                self._close_player()
                return
            # Jitter buffer kecil (~160ms = 8 paket x 20ms) agar tahan jitter WiFi sebelum mulai diputar
            if not self.prebuf_ready:
                self.prebuf.append(payload)
                if len(self.prebuf) >= self.PREBUFFER_PACKETS:
                    self.player_proc.stdin.write(b"".join(self.prebuf))
                    self.player_proc.stdin.flush()
                    self.prebuf = []
                    self.prebuf_ready = True
            else:
                self.player_proc.stdin.write(payload)
                self.player_proc.stdin.flush()
        except Exception:
            self._close_player()

    def _run_loop(self):
        """Loop utama: dengarkan semua channel RTP, buang duplikat, dan rebind otomatis jika jaringan berubah."""
        while self.is_running and not self._bind_sockets():
            time.sleep(1)

        last_net_check = time.time()
        while self.is_running:
            try:
                # Deteksi perubahan jaringan (DHCP baru / pindah AP WiFi / adapter naik-turun) tiap 5 detik
                if time.time() - last_net_check > 5.0:
                    last_net_check = time.time()
                    if self._local_ips() != self.net_sig:
                        print("[*] Perubahan jaringan terdeteksi, menyambung ulang listener RTP...")
                        self._bind_sockets()
                        threading.Thread(target=lambda: self.send_heartbeat(force_update=False), daemon=True).start()

                if not self.sockets:
                    time.sleep(1)
                    self._bind_sockets()
                    continue

                readable, _, _ = select.select(self.sockets, [], [], 0.25)
                for sock in readable:
                    try:
                        data, addr = sock.recvfrom(2048)
                    except Exception:
                        continue
                    self._handle_packet(sock, data, addr)

                # Siaran dianggap berhenti jika tidak ada paket valid > 1.2 detik
                if self.status == "STREAMING" and (time.time() - self.last_packet_time > 1.2):
                    self._close_player()
                    self.set_status("STANDBY", "biasa", "")

            except Exception:
                time.sleep(0.05)

        self._close_player()

    def play_test_chime(self):
        """Memutar nada bel uji coba langsung ke soundcard Windows / amplifier."""
        # 1. Picu push notifikasi SEKETIKA (pada saat tombol diklik, bukan setelahnya!)
        self.notify_toast(
            "IntanWave — Uji Coba Audio",
            "Memutar nada bel ding-dong ke speaker terminal."
        )

        # 2. Putar audio di background thread agar tidak ada blocking UI
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
                    # 1. Coba via winsound
                    if sys.platform == "win32":
                        try:
                            import winsound
                            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            return
                        except Exception as e:
                            print("Winsound error:", e)

                    # 2. Fallback via ffplay langsung
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

            # Fallback terakhir jika file wav tidak ada
            if sys.platform == "win32":
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        threading.Thread(target=_play_audio, daemon=True).start()
        return True
