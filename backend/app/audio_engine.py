import subprocess
import threading
import time
import random
import shutil
from pathlib import Path
from typing import Optional, Callable, List
from app.config import DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT, AUDIO_DIR, BASE_DIR
from app.database import log_event, get_settings, get_db
from app.stream_hub import stream_hub

class AudioEngine:
    def __init__(self):
        self.status = "IDLE"  # IDLE, STREAMING, STOPPED
        self.current_title = ""
        self.current_file = ""
        self.current_category = "biasa"
        self.duration = 0.0
        self.started_at = 0.0
        self.elapsed = 0.0
        self.enable_multicast = True
        self.enable_local = False
        self.target_desc = "Semua Speaker (Multicast)"

        self.multicast_proc: Optional[subprocess.Popen] = None
        self.local_proc: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._last_test_cooldown = {}
        self.listeners: List[Callable[[dict], None]] = []

    def get_audio_duration(self, file_path: str) -> float:
        """Mengambil durasi file audio menggunakan ffprobe."""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                alt = AUDIO_DIR / path_obj.name
                if alt.exists():
                    file_path = str(alt.resolve())
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def add_listener(self, callback: Callable[[dict], None]):
        self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[dict], None]):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def notify_listeners(self):
        state = self.get_status()
        for cb in list(self.listeners):
            try:
                cb(state)
            except Exception:
                pass

    def get_status(self) -> dict:
        if self.status == "STREAMING" and self.started_at > 0:
            self.elapsed = min(time.time() - self.started_at, self.duration)
        else:
            self.elapsed = 0.0

        return {
            "status": self.status,
            "title": self.current_title,
            "file": self.current_file,
            "category": self.current_category,
            "duration": round(self.duration, 1),
            "elapsed": round(self.elapsed, 1),
            "enable_multicast": self.enable_multicast,
            "enable_local": self.enable_local,
            "target_desc": self.target_desc,
            "multicast_dest": f"{get_settings().get('multicast_ip', DEFAULT_MULTICAST_IP)}:{get_settings().get('multicast_port', DEFAULT_MULTICAST_PORT)}"
        }

    def play(
        self, 
        file_path: str, 
        title: str, 
        enable_multicast: Optional[bool] = None, 
        enable_local: Optional[bool] = None,
        target_endpoints: Optional[List[str]] = None,
        target_desc: Optional[str] = None,
        category: str = "biasa"
    ):
        """
        Memulai playback ke target RTP (Multicast atau Selective Unicast via tee muxer)
        dan/atau Windows Audio lokal.
        """
        with self._lock:
            path_obj = Path(file_path)
            now = time.time()
            # Anti double-click: abaikan jika audio yang sama dipanggil berulang dalam tempo < 0.8s
            if self.status == "STREAMING" and self.current_file == path_obj.name and (now - self.started_at < 0.8):
                return

            self.stop()  # Hentikan stream yang sedang berjalan jika ada

            if not path_obj.exists():
                # Robust fallback jika file_path berupa path host OS lain (misal D:\... di Linux container)
                alt_path = AUDIO_DIR / path_obj.name
                if alt_path.exists():
                    path_obj = alt_path
                else:
                    log_event("PLAYBACK_ERROR", f"File tidak ditemukan: {file_path} (maupun di {AUDIO_DIR})", level="ERROR")
                    raise FileNotFoundError(f"File audio '{path_obj.name}' tidak ditemukan di storage server")

        settings = get_settings()
        mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
        mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
        
        self.enable_multicast = enable_multicast if enable_multicast is not None else (settings.get("enable_multicast", "true") == "true")
        self.enable_local = enable_local if enable_local is not None else (settings.get("enable_local", "false") == "true")
        self.target_desc = target_desc or "Semua Speaker"

        self.current_title = title
        self.current_file = path_obj.name
        self.current_category = category or "biasa"
        self.duration = self.get_audio_duration(file_path)
        self.started_at = time.time()
        self.status = "STREAMING"
        self._stop_event.clear()

        # 1. Klasifikasi target:
        #    - speaker fisik / multicast  -> RTP
        #    - PC client Windows (node)   -> HTTP stream (/api/stream), tanpa RTP/multicast/dedup
        rtp_endpoints = list(dict.fromkeys(target_endpoints)) if target_endpoints else None
        http_all = False
        http_nodes = set()
        if self.enable_multicast:
            mc_ep = f"{mc_ip}:{mc_port}"
            if rtp_endpoints is None or mc_ep in (rtp_endpoints or []):
                http_all = True  # siaran global / multicast: semua node ikut
            node_by_ip = self._get_node_ip_map()
            kept = []
            for ep in (rtp_endpoints or []):
                ip = ep.split(":")[0]
                if ip in node_by_ip:
                    http_nodes.add(node_by_ip[ip])
                else:
                    kept.append(ep)
            rtp_endpoints = kept
        use_http = self.enable_multicast and (http_all or bool(http_nodes))

        # Output RTP (speaker fisik / multicast)
        rtp_list = []
        if self.enable_multicast:
            rtp_list = rtp_endpoints if rtp_endpoints is not None else [f"{mc_ip}:{mc_port}"]

        net_cmd_args = []
        if rtp_list:
            if len(rtp_list) == 1:
                net_cmd_args.extend([
                    "-map", "0:a",
                    "-af", "aresample=8000:async=1,asetnsamples=n=160",
                    "-c:a", "pcm_alaw",
                    "-ac", "1",
                    "-f", "rtp", f"rtp://{rtp_list[0]}?pkt_size=172"
                ])
            else:
                # tee muxer: beberapa output RTP sekaligus dengan SSRC sinkron
                shared_ssrc = random.randint(1, 2**31 - 1)
                slaves = [
                    f"[select=a:f=rtp:ssrc={shared_ssrc}:seq=0]rtp://{ep}?pkt_size=172"
                    for ep in rtp_list
                ]
                net_cmd_args.extend([
                    "-map", "0:a",
                    "-af", "aresample=8000:async=1,asetnsamples=n=160",
                    "-c:a", "pcm_alaw",
                    "-ac", "1",
                    "-f", "tee", "|".join(slaves)
                ])

        if use_http:
            # Dual-Stream HD: 44.1kHz 16-bit PCM mono (882 sample / 1764 byte per 20ms)
            # Jernih selevel CD untuk PC client, zero-buffer, zero-latency
            net_cmd_args.extend([
                "-map", "0:a",
                "-af", "aresample=44100:async=1,asetnsamples=n=882",
                "-c:a", "pcm_s16le",
                "-ac", "1",
                "-f", "s16le",
                "-flush_packets", "1",
                "pipe:1"
            ])

        if net_cmd_args:
            net_cmd = [
                "ffmpeg", "-re", "-y",
                "-i", str(path_obj.resolve()),
                *net_cmd_args
            ]
            try:
                if use_http:
                    stream_hub.begin(all_nodes=http_all, nodes=http_nodes)
                self.multicast_proc = subprocess.Popen(
                    net_cmd,
                    stdout=subprocess.PIPE if use_http else subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                if use_http:
                    threading.Thread(
                        target=self._pump_stream, args=(self.multicast_proc,), daemon=True
                    ).start()
            except Exception as e:
                stream_hub.end()
                log_event("RTP_ERROR", f"Gagal menjalankan ffmpeg stream: {e}", level="ERROR")

        # 2. Output Windows Audio (ffplay ke speaker lokal)
        if self.enable_local:
            local_cmd = [
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                str(path_obj.resolve())
            ]
            try:
                self.local_proc = subprocess.Popen(
                    local_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
            except Exception as e:
                log_event("LOCAL_AUDIO_ERROR", f"Gagal menjalankan ffplay lokal: {e}", level="ERROR")

        log_event("PLAYBACK_STARTED", f"Memutar '{title}' -> {self.target_desc} (Multicast={self.enable_multicast}, Local={self.enable_local})")
        self.notify_listeners()

        # Monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
        self.monitor_thread.start()

    def test_speaker_audio(self, ip: str, port: int = 5004, node_id: Optional[str] = None):
        """Memutar jingle test pendek langsung ke satu speaker tertentu (RTP untuk speaker fisik, HTTP stream untuk PC Node)."""
        with self._lock:
            now = time.time()
            cooldown_key = f"{ip}:{node_id or ''}"
            if cooldown_key in self._last_test_cooldown and (now - self._last_test_cooldown[cooldown_key] < 1.5):
                return
            self._last_test_cooldown[cooldown_key] = now

            chime_path = AUDIO_DIR / "test_chime.wav"
            if not chime_path.exists():
                raise FileNotFoundError("Berkas test_chime.wav tidak ditemukan")

        # Cek apakah target adalah PC Node
        node_map = self._get_node_ip_map()
        target_node = node_id or node_map.get(ip)

        if target_node:
            cmd = [
                "ffmpeg", "-re", "-y",
                "-i", str(chime_path.resolve()),
                "-af", "aresample=44100:async=1,asetnsamples=n=882",
                "-c:a", "pcm_s16le",
                "-ac", "1",
                "-f", "s16le", "-flush_packets", "1",
                "pipe:1"
            ]
            try:
                stream_hub.begin(all_nodes=False, nodes={target_node})
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                def _pump():
                    try:
                        while True:
                            chunk = proc.stdout.read(1764)
                            if not chunk:
                                break
                            stream_hub.publish(chunk)
                    finally:
                        stream_hub.end()
                threading.Thread(target=_pump, daemon=True).start()
                log_event("TEST_AUDIO", f"Mengirimkan uji suara HD ke PC Node {target_node} ({ip})")
                return
            except Exception as e:
                stream_hub.end()
                log_event("TEST_AUDIO_ERROR", f"Gagal uji suara HD ke PC Node {target_node}: {e}", level="ERROR")
                raise e

        # Target adalah speaker fisik (RTP)
        rtp_url = f"rtp://{ip}:{port}?pkt_size=172"
        cmd = [
            "ffmpeg", "-re", "-y",
            "-i", str(chime_path.resolve()),
            "-af", "aresample=8000:async=1,asetnsamples=n=160",
            "-acodec", "pcm_alaw",
            "-ac", "1",
            "-f", "rtp",
            rtp_url
        ]
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )
            log_event("TEST_AUDIO", f"Mengirimkan uji suara RTP ke {ip}:{port}")
        except Exception as e:
            log_event("TEST_AUDIO_ERROR", f"Gagal uji suara ke {ip}: {e}", level="ERROR")
            raise e

    def _monitor_playback(self):
        """Thread background untuk update elapsed dan mendeteksi selesainya lagu."""
        while not self._stop_event.is_set():
            time.sleep(0.5)

            mc_done = (self.multicast_proc is None) or (self.multicast_proc.poll() is not None)
            local_done = (self.local_proc is None) or (self.local_proc.poll() is not None)

            if mc_done and local_done:
                break

            self.notify_listeners()

        if not self._stop_event.is_set():
            self._cleanup_processes()
            self.status = "IDLE"
            self.current_category = "biasa"
            self.started_at = 0.0
            log_event("PLAYBACK_FINISHED", f"Selesai memutar '{self.current_title}'")
            self.notify_listeners()

    def stop(self):
        """Menghentikan seluruh pemutaran audio seketika."""
        with self._lock:
            self._stop_event.set()
            self._cleanup_processes()
            was_streaming = (self.status == "STREAMING")
            self.status = "IDLE"
            self.current_category = "biasa"
            self.started_at = 0.0
            self.elapsed = 0.0
            if was_streaming:
                log_event("PLAYBACK_STOPPED", f"Siaran dihentikan manual: '{self.current_title}'")
            self.notify_listeners()

    def _cleanup_processes(self):
        for proc in [self.multicast_proc, self.local_proc]:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        self.multicast_proc = None
        self.local_proc = None
        stream_hub.end()

    @staticmethod
    def _get_node_ip_map() -> dict:
        """Peta IP -> node_id untuk PC client Windows (node) yang aktif. Node menerima audio via HTTP, bukan RTP."""
        try:
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT ip_address, node_id FROM speakers "
                    "WHERE enabled = 1 AND device_type = 'node' AND node_id IS NOT NULL AND node_id != ''"
                ).fetchall()
            return {r["ip_address"]: r["node_id"] for r in rows}
        except Exception:
            return {}

    @staticmethod
    def _pump_stream(proc):
        """Baca PCM 16-bit 44.1kHz dari stdout FFmpeg (1764 byte per ~20ms) lalu bagikan ke semua client HTTP/WS."""
        try:
            while True:
                chunk = proc.stdout.read(1764)
                if not chunk:
                    break
                stream_hub.publish(chunk)
        except Exception:
            pass
        finally:
            stream_hub.end()

audio_engine = AudioEngine()
