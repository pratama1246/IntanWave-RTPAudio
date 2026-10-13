import subprocess
import threading
import time
import shutil
from pathlib import Path
from typing import Optional, Callable, List
from app.config import DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT, AUDIO_DIR, BASE_DIR
from app.database import log_event, get_settings

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
        self.stop()  # Hentikan stream yang sedang berjalan jika ada

        path_obj = Path(file_path)
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

        # 1. Output RTP (Multicast atau Selektif)
        if self.enable_multicast:
            # Tentukan output destinations
            if target_endpoints and len(target_endpoints) > 0:
                if len(target_endpoints) == 1:
                    rtp_args = [
                        "-acodec", "pcm_alaw",
                        "-ar", "8000",
                        "-ac", "1",
                        "-f", "rtp", f"rtp://{target_endpoints[0]}"
                    ]
                else:
                    # FFmpeg tee muxer untuk multiple unicast outputs
                    tee_outputs = "|".join([f"[select=a:f=rtp]rtp://{ep}" for ep in target_endpoints])
                    rtp_args = [
                        "-map", "0:a",
                        "-c:a", "pcm_alaw",
                        "-ar", "8000",
                        "-ac", "1",
                        "-f", "tee", tee_outputs
                    ]
            else:
                # Default global multicast
                rtp_args = [
                    "-acodec", "pcm_alaw",
                    "-ar", "8000",
                    "-ac", "1",
                    "-f", "rtp", f"rtp://{mc_ip}:{mc_port}"
                ]

            rtp_cmd = [
                "ffmpeg", "-re", "-y",
                "-i", str(path_obj.resolve()),
                *rtp_args
            ]
            try:
                self.multicast_proc = subprocess.Popen(
                    rtp_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
            except Exception as e:
                log_event("RTP_ERROR", f"Gagal menjalankan RTP ffmpeg: {e}", level="ERROR")

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

    def test_speaker_audio(self, ip: str, port: int = 5004):
        """Memutar jingle test pendek langsung ke satu speaker tertentu."""
        chime_path = AUDIO_DIR / "test_chime.wav"
        if not chime_path.exists():
            raise FileNotFoundError("Berkas test_chime.wav tidak ditemukan")

        rtp_url = f"rtp://{ip}:{port}"
        cmd = [
            "ffmpeg", "-re", "-y",
            "-i", str(chime_path.resolve()),
            "-acodec", "pcm_alaw",
            "-ar", "8000",
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
            log_event("TEST_AUDIO", f"Mengirimkan uji suara ke {ip}:{port}")
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

audio_engine = AudioEngine()
