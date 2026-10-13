import os
import sys
import json
import time
import socket
import struct
import threading
import subprocess
import shutil
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
    def __init__(self, on_status_change=None):
        self.config = self.load_config()
        self.multicast_ip = self.config.get("multicast_ip", "239.255.0.1")
        self.multicast_port = int(self.config.get("multicast_port", 5004))
        self.device_name = self.config.get("device_name", "Terminal Audio (Amplifier)")
        
        self.status = "STANDBY"  # STANDBY | STREAMING
        self.is_running = False
        self.on_status_change = on_status_change
        
        self.player_proc = None
        self.last_packet_time = 0
        self.sock = None
        self.thread = None
        self.last_toast_time = 0
        
        # RTP Sequence Number Deduplication (Mencegah gema/suara dobel)
        self.seen_seqs = set()
        self.seen_seq_history = []
        self.max_history = 512

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "multicast_ip": "239.255.0.1",
            "multicast_port": 5004,
            "device_name": "Terminal Audio (Amplifier)",
            "enable_toast": True
        }

    def save_config(self, ip, port, device_name=None):
        """Menyimpan konfigurasi baru dan me-restart socket receiver."""
        self.multicast_ip = ip.strip()
        self.multicast_port = int(port)
        if device_name:
            self.device_name = device_name.strip()
            
        data = {
            "multicast_ip": self.multicast_ip,
            "multicast_port": self.multicast_port,
            "device_name": self.device_name,
            "enable_toast": self.config.get("enable_toast", True)
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

    def set_status(self, new_status):
        if self.status != new_status:
            self.status = new_status
            if self.on_status_change:
                self.on_status_change(new_status)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        self._close_player()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def _close_player(self):
        if self.player_proc:
            try:
                if self.player_proc.stdin:
                    self.player_proc.stdin.close()
            except Exception:
                pass
            try:
                self.player_proc.wait(timeout=0.3)
            except Exception:
                try:
                    self.player_proc.kill()
                except Exception:
                    pass
            self.player_proc = None
        self.seen_seqs.clear()
        self.seen_seq_history.clear()

    def _run_loop(self):
        """Loop utama background mendengarkan paket RTP Multicast atau Unicast."""
        while self.is_running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind(("", self.multicast_port))
                
                # Cek apakah alamat tujuan adalah Multicast (224.0.0.0 - 239.255.255.255)
                is_multicast = False
                try:
                    first_octet = int(self.multicast_ip.strip().split(".")[0])
                    is_multicast = (224 <= first_octet <= 239)
                except Exception:
                    pass

                if is_multicast:
                    # Join Multicast Group pada default adapter (INADDR_ANY)
                    try:
                        mreq = struct.pack("4sl", socket.inet_aton(self.multicast_ip), socket.INADDR_ANY)
                        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
                    except Exception as e:
                        print("Warning: gagal bind INADDR_ANY multicast:", e)

                    # Join pada semua adapter jaringan aktif (Ethernet, WiFi, dll)
                    # untuk memastikan paket diterima meski ada multiple NIC
                    try:
                        hostname = socket.gethostname()
                        for iface_ip in socket.gethostbyname_ex(hostname)[2]:
                            if not iface_ip.startswith("127."):
                                try:
                                    mreq_if = struct.pack("4s4s", socket.inet_aton(self.multicast_ip), socket.inet_aton(iface_ip))
                                    self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq_if)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                self.sock.settimeout(0.5)
                break
            except Exception as e:
                print(f"Gagal bind socket ({e}), mencoba kembali...")
                time.sleep(1)

        print(f"[*] IntanWave Node standby pada rtp://{self.multicast_ip}:{self.multicast_port}")

        while self.is_running:
            try:
                data, _ = self.sock.recvfrom(2048)
                now = time.time()
                self.last_packet_time = now

                # Parsing Header RTP RFC 3550
                if len(data) >= 12:
                    b0 = data[0]
                    cc = b0 & 0x0F
                    x_bit = (b0 >> 4) & 0x01
                    seq_num = struct.unpack("!H", data[2:4])[0]

                    # Deduplikasi RTP: abaikan paket jika seq_num sudah pernah diproses baru-baru ini
                    # Mencegah echo/gema akibat paket ganda (Unicast + Multicast bersamaan)
                    if seq_num in self.seen_seqs:
                        continue

                    self.seen_seqs.add(seq_num)
                    self.seen_seq_history.append(seq_num)
                    if len(self.seen_seq_history) > self.max_history:
                        oldest = self.seen_seq_history.pop(0)
                        self.seen_seqs.discard(oldest)

                    offset = 12 + (cc * 4)
                    if x_bit and len(data) >= offset + 4:
                        ext_len = struct.unpack("!H", data[offset + 2:offset + 4])[0]
                        offset += 4 + (ext_len * 4)

                    payload = data[offset:] if len(data) > offset else None

                    # Jika player belum jalan, picu notifikasi dan mulai ffplay baru
                    if payload:
                        if self.player_proc is None:
                            # 1. Picu notifikasi SEKETIKA saat paket pertama masuk
                            self.notify_toast(
                                "IntanWave — Siaran Masuk",
                                f"Sedang mengudara ke {self.device_name}"
                            )
                            self.set_status("STREAMING")

                            vol = int(self.config.get("volume", 100))
                            vol = max(0, min(100, vol))
                            
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
                                "-f", "alaw",
                                "-ar", "8000",
                                "-ac", "1",
                                "-i", "-"
                            ]
                            self.player_proc = subprocess.Popen(
                                cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                            )

                        # Tulis audio payload ke stdin ffplay
                        if self.player_proc and self.player_proc.stdin:
                            try:
                                if self.player_proc.poll() is not None:
                                    self._close_player()
                                else:
                                    self.player_proc.stdin.write(payload)
                                    self.player_proc.stdin.flush()
                            except Exception:
                                self._close_player()

            except socket.timeout:
                # Cek apakah aliran paket berhenti > 1.2 detik
                if self.status == "STREAMING" and (time.time() - self.last_packet_time > 1.2):
                    self._close_player()
                    self.set_status("STANDBY")

            except Exception:
                time.sleep(0.1)

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
            if sys.platform == "win32":
                import winsound
                candidates = [
                    EXE_DIR / "test_chime.wav",
                    BUNDLE_DIR / "test_chime.wav"
                ]
                for candidate in candidates:
                    if candidate.exists():
                        try:
                            winsound.PlaySound(str(candidate.resolve()), winsound.SND_FILENAME)
                            return
                        except Exception as e:
                            print("Winsound error:", e)

                # Fallback jika file wav tidak ada
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        threading.Thread(target=_play_audio, daemon=True).start()
        return True
