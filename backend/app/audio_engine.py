import subprocess
import threading
import time
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, List, Dict, Set, Tuple
from app.config import DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT, AUDIO_DIR
from app.database import log_event, get_settings


@dataclass
class PlaybackSession:
    session_id: str
    title: str
    file_name: str
    file_path: str
    category: str
    priority: int  # 1=Darurat, 2=Safety, 3=Biasa
    duration: float
    started_at: float
    enable_multicast: bool
    enable_local: bool
    target_desc: str
    target_endpoints: Optional[List[str]]
    footprint: Set[str]
    multicast_proc: Optional[subprocess.Popen] = None
    local_proc: Optional[subprocess.Popen] = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    monitor_thread: Optional[threading.Thread] = None


@dataclass
class QueuedPlayback:
    queue_id: str
    file_path: str
    title: str
    enable_multicast: Optional[bool]
    enable_local: Optional[bool]
    target_endpoints: Optional[List[str]]
    target_desc: Optional[str]
    category: str
    priority: int
    is_manual: bool
    created_at: float
    footprint: Set[str]


def resolve_audio_category(category: str = "", filename: str = "", title: str = "") -> Tuple[str, int]:
    """
    Menentukan kategori ('darurat', 'safety', 'biasa') dan level prioritas (1, 2, 3)
    berdasarkan kategori terdaftar atau pencocokan kata kunci pada nama file/judul.
    """
    cat = (category or "").lower().strip()
    fn = (filename or "").lower()
    tt = (title or "").lower()
    combined = f"{cat} {fn} {tt}"

    # 1. Cek Darurat / Emergency (P1)
    if cat == "darurat" or any(k in combined for k in [
        "darurat", "siren", "sirine", "ews", "emergency", "bahaya", "evakuasi", "kebakaran", "gempa", "tsunami"
    ]):
        return "darurat", 1

    # 2. Cek Safety / K3 (P2)
    if cat in ("safety", "k3") or any(k in combined for k in [
        "safety", "k3", "keselamatan", "apd", "pelindung", "briefing", "peringatan", "instruksi", "pengumuman"
    ]):
        return "safety", 2

    # 3. Default Biasa / Rutin (P3)
    return "biasa", 3


def get_audio_priority(category: str, filename: str = "", title: str = "") -> int:
    _, prio = resolve_audio_category(category, filename, title)
    return prio



def footprints_overlap(fp1: Set[str], fp2: Set[str]) -> bool:
    if ("ALL_RTP" in fp1 and any(k.startswith("rtp:") or k == "ALL_RTP" for k in fp2)) or \
       ("ALL_RTP" in fp2 and any(k.startswith("rtp:") or k == "ALL_RTP" for k in fp1)):
        return True
    if bool(fp1.intersection(fp2)):
        return True
    return False


class AudioEngine:
    def __init__(self):
        self._lock = threading.RLock()
        self.active_sessions: Dict[str, PlaybackSession] = {}
        self.playback_queue: List[QueuedPlayback] = []
        self.listeners: List[Callable[[dict], None]] = []
        self._last_test_cooldown: Dict[str, float] = {}

        # Fallback atribut kompatibilitas
        self.status = "IDLE"
        self.current_title = ""
        self.current_file = ""
        self.current_category = "biasa"
        self.duration = 0.0
        self.started_at = 0.0
        self.elapsed = 0.0
        self.enable_multicast = True
        self.enable_local = False
        self.target_desc = "Semua Speaker"

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
        with self._lock:
            primary_session = None
            if self.active_sessions:
                primary_session = min(
                    self.active_sessions.values(),
                    key=lambda s: (s.priority, -s.started_at)
                )

            if primary_session and primary_session.started_at > 0:
                elapsed = min(time.time() - primary_session.started_at, primary_session.duration)
                status_str = "STREAMING"
                title = primary_session.title
                filename = primary_session.file_name
                category = primary_session.category
                priority_val = primary_session.priority
                duration = round(primary_session.duration, 1)
                elapsed_val = round(elapsed, 1)
                enable_mc = primary_session.enable_multicast
                enable_loc = primary_session.enable_local
                target_desc = primary_session.target_desc
            else:
                status_str = "IDLE"
                title = ""
                filename = ""
                category = "biasa"
                priority_val = 3
                duration = 0.0
                elapsed_val = 0.0
                enable_mc = True
                enable_loc = False
                target_desc = "Semua Speaker"

            active_list = []
            for s in self.active_sessions.values():
                s_elapsed = min(time.time() - s.started_at, s.duration) if s.started_at > 0 else 0.0
                active_list.append({
                    "session_id": s.session_id,
                    "title": s.title,
                    "file": s.file_name,
                    "category": s.category,
                    "priority": s.priority,
                    "duration": round(s.duration, 1),
                    "elapsed": round(s_elapsed, 1),
                    "target_desc": s.target_desc,
                    "enable_multicast": s.enable_multicast,
                    "enable_local": s.enable_local,
                    "started_at": s.started_at
                })

            queue_list = []
            for q in self.playback_queue:
                queue_list.append({
                    "queue_id": q.queue_id,
                    "title": q.title,
                    "category": q.category,
                    "priority": q.priority,
                    "target_desc": q.target_desc,
                    "created_at": q.created_at,
                    "is_manual": q.is_manual
                })

            settings = get_settings()
            mc_dest = f"{settings.get('multicast_ip', DEFAULT_MULTICAST_IP)}:{settings.get('multicast_port', DEFAULT_MULTICAST_PORT)}"

            return {
                "status": status_str,
                "title": title,
                "file": filename,
                "category": category,
                "priority": priority_val,
                "duration": duration,
                "elapsed": elapsed_val,
                "enable_multicast": enable_mc,
                "enable_local": enable_loc,
                "target_desc": target_desc,
                "multicast_dest": mc_dest,
                "active_sessions_count": len(self.active_sessions),
                "active_sessions": active_list,
                "queue_count": len(self.playback_queue),
                "queue": queue_list
            }

    def _calculate_footprint(
        self,
        enable_multicast: bool,
        enable_local: bool,
        target_endpoints: Optional[List[str]],
        mc_ip: str,
        mc_port: str
    ) -> Tuple[Set[str], List[str]]:
        footprint: Set[str] = set()
        mc_ep = f"{mc_ip}:{mc_port}"
        rtp_list = list(dict.fromkeys(target_endpoints)) if target_endpoints else []

        if not rtp_list:
            rtp_list = [mc_ep]
            footprint.add("ALL_RTP")
        else:
            if mc_ep in rtp_list or enable_multicast:
                footprint.add("ALL_RTP")
            for ep in rtp_list:
                footprint.add(f"rtp:{ep}")

        if enable_local:
            footprint.add("LOCAL")

        return footprint, rtp_list

    def play(
        self,
        file_path: str,
        title: str,
        enable_multicast: Optional[bool] = None,
        enable_local: Optional[bool] = None,
        target_endpoints: Optional[List[str]] = None,
        target_desc: Optional[str] = None,
        category: str = "biasa",
        is_manual: bool = True
    ) -> dict:
        """
        Memulai playback audio dengan Multi-Zone Parallel Streaming & Priority Queue.
        Jika target speaker berbeda/disjoint, streaming berjalan paralel tanpa saling potong.
        Jika target speaker bentrok:
        - Manual trigger atau prioritas lebih tinggi akan memotong stream lama.
        - Jadwal otomatis dengan prioritas sama/rendah dimasukkan ke antrean FIFO.
        """
        path_obj = Path(file_path)
        if not path_obj.exists():
            alt_path = AUDIO_DIR / path_obj.name
            if alt_path.exists():
                path_obj = alt_path
            else:
                log_event("PLAYBACK_ERROR", f"File tidak ditemukan: {file_path}", level="ERROR")
                raise FileNotFoundError(f"File audio '{path_obj.name}' tidak ditemukan di storage server")

        settings = get_settings()
        mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
        mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
        mc_enabled = enable_multicast if enable_multicast is not None else (settings.get("enable_multicast", "true") == "true")
        loc_enabled = enable_local if enable_local is not None else (settings.get("enable_local", "false") == "true")
        desc = target_desc or "Semua Speaker"
        resolved_cat, prio = resolve_audio_category(category, path_obj.name, title)

        footprint, rtp_list = self._calculate_footprint(
            enable_multicast=mc_enabled,
            enable_local=loc_enabled,
            target_endpoints=target_endpoints,
            mc_ip=mc_ip,
            mc_port=mc_port
        )

        now = time.time()

        with self._lock:
            overlapping = [s for s in self.active_sessions.values() if footprints_overlap(s.footprint, footprint)]

            # Anti double-click
            if is_manual:
                for s in overlapping:
                    if s.file_name == path_obj.name and (now - s.started_at < 0.8):
                        return {"status": "IGNORED", "message": "Anti double-click cooldown"}

            if overlapping:
                if is_manual:
                    for s in overlapping:
                        self._stop_session_locked(s.session_id, reason="OVERRIDDEN")
                        log_event("PLAYBACK_OVERRIDDEN", f"Siaran manual '{title}' memotong siaran aktif '{s.title}' pada target yang sama")
                else:
                    highest_active_prio = min(s.priority for s in overlapping)
                    if prio < highest_active_prio:
                        for s in overlapping:
                            self._stop_session_locked(s.session_id, reason="PREEMPTED")
                            log_event("PLAYBACK_PREEMPTED", f"Audio prioritas tinggi '{title}' (P{prio}) memotong siaran '{s.title}' (P{s.priority})")
                    else:
                        q_item = QueuedPlayback(
                            queue_id=uuid.uuid4().hex[:8],
                            file_path=str(path_obj.resolve()),
                            title=title,
                            enable_multicast=mc_enabled,
                            enable_local=loc_enabled,
                            target_endpoints=target_endpoints,
                            target_desc=desc,
                            category=resolved_cat,
                            priority=prio,
                            is_manual=False,
                            created_at=time.time(),
                            footprint=footprint
                        )
                        self.playback_queue.append(q_item)
                        self.playback_queue.sort(key=lambda x: (x.priority, x.created_at))
                        active_titles = ", ".join(s.title for s in overlapping)
                        log_event("SCHEDULE_QUEUED", f"Jadwal '{title}' (P{prio}) dimasukkan ke antrean karena speaker sedang memutar '{active_titles}'")
                        self.notify_listeners()
                        return {"status": "QUEUED", "queue_id": q_item.queue_id, "title": title}

            session_id = self._start_session_locked(
                file_path=str(path_obj.resolve()),
                file_name=path_obj.name,
                title=title,
                category=resolved_cat,
                priority=prio,
                enable_multicast=mc_enabled,
                enable_local=loc_enabled,
                target_desc=desc,
                target_endpoints=target_endpoints,
                footprint=footprint,
                rtp_list=rtp_list
            )

        self.notify_listeners()
        return {"status": "STREAMING", "session_id": session_id, "title": title}

    def _start_session_locked(
        self,
        file_path: str,
        file_name: str,
        title: str,
        category: str,
        priority: int,
        enable_multicast: bool,
        enable_local: bool,
        target_desc: str,
        target_endpoints: Optional[List[str]],
        footprint: Set[str],
        rtp_list: List[str]
    ) -> str:
        session_id = uuid.uuid4().hex[:8]
        duration = self.get_audio_duration(file_path)
        path_obj = Path(file_path)

        session = PlaybackSession(
            session_id=session_id,
            title=title,
            file_name=file_name,
            file_path=file_path,
            category=category,
            priority=priority,
            duration=duration,
            started_at=time.time(),
            enable_multicast=enable_multicast,
            enable_local=enable_local,
            target_desc=target_desc,
            target_endpoints=target_endpoints,
            footprint=footprint
        )

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

        if net_cmd_args:
            net_cmd = [
                "ffmpeg", "-re", "-y",
                "-i", str(path_obj.resolve()),
                *net_cmd_args
            ]
            try:
                session.multicast_proc = subprocess.Popen(
                    net_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
                log_event("PLAYBACK_START", f"Memulai siaran '{title}' (P{priority}/{category}) ke {target_desc} [{len(rtp_list)} endpoint RTP]")
            except Exception as e:
                log_event("RTP_ERROR", f"Gagal menjalankan ffmpeg stream sesi {session_id}: {e}", level="ERROR")

        if enable_local:
            local_cmd = [
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                str(path_obj.resolve())
            ]
            try:
                session.local_proc = subprocess.Popen(
                    local_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
                )
            except Exception as e:
                log_event("LOCAL_AUDIO_ERROR", f"Gagal menjalankan ffplay lokal sesi {session_id}: {e}", level="ERROR")

        self.active_sessions[session_id] = session

        t_mon = threading.Thread(
            target=self._monitor_session,
            args=(session,),
            daemon=True
        )
        session.monitor_thread = t_mon
        t_mon.start()

        log_event("PLAYBACK_STARTED", f"Memutar '{title}' -> {target_desc} (P{priority}, Sesi={session_id})")
        return session_id

    def _monitor_session(self, session: PlaybackSession):
        """Thread background pemantau progres dan deteksi selesainya sesi pemutaran tertentu."""
        while not session.stop_event.is_set():
            time.sleep(0.5)

            mc_done = (session.multicast_proc is None) or (session.multicast_proc.poll() is not None)
            local_done = (session.local_proc is None) or (session.local_proc.poll() is not None)

            if session.multicast_proc is None and session.local_proc is None:
                elapsed = time.time() - session.started_at
                if elapsed >= max(session.duration, 1.0):
                    break
            elif mc_done and local_done:
                break

            self.notify_listeners()

        with self._lock:
            self._cleanup_session_procs(session)
            was_active = self.active_sessions.pop(session.session_id, None) is not None
            if was_active and not session.stop_event.is_set():
                log_event("PLAYBACK_FINISHED", f"Selesai memutar '{session.title}' (Sesi={session.session_id})")

            self._process_queue_locked()

        self.notify_listeners()

    def _stop_session_locked(self, session_id: str, reason: str = "STOPPED"):
        session = self.active_sessions.pop(session_id, None)
        if not session:
            return
        session.stop_event.set()
        self._cleanup_session_procs(session)
        if reason == "STOPPED":
            log_event("PLAYBACK_STOPPED", f"Siaran dihentikan manual: '{session.title}' (Sesi={session_id})")

    def _cleanup_session_procs(self, session: PlaybackSession):
        for proc in [session.multicast_proc, session.local_proc]:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=0.4)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        session.multicast_proc = None
        session.local_proc = None

    def _process_queue_locked(self):
        """Mengecek antrean playback dan menjalankan item yang speaker targetnya sudah bebas."""
        if not self.playback_queue:
            return

        remaining_queue: List[QueuedPlayback] = []
        self.playback_queue.sort(key=lambda x: (x.priority, x.created_at))

        for candidate in self.playback_queue:
            overlaps = any(
                footprints_overlap(candidate.footprint, s.footprint)
                for s in self.active_sessions.values()
            )
            if not overlaps:
                try:
                    settings = get_settings()
                    mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
                    mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))

                    footprint, rtp_list = self._calculate_footprint(
                        enable_multicast=bool(candidate.enable_multicast),
                        enable_local=bool(candidate.enable_local),
                        target_endpoints=candidate.target_endpoints,
                        mc_ip=mc_ip,
                        mc_port=mc_port
                    )

                    path_obj = Path(candidate.file_path)
                    log_event("SCHEDULE_DEQUEUED", f"Menjalankan jadwal antrean: '{candidate.title}' -> {candidate.target_desc}")

                    self._start_session_locked(
                        file_path=candidate.file_path,
                        file_name=path_obj.name,
                        title=candidate.title,
                        category=candidate.category,
                        priority=candidate.priority,
                        enable_multicast=bool(candidate.enable_multicast),
                        enable_local=bool(candidate.enable_local),
                        target_desc=candidate.target_desc or "Semua Speaker",
                        target_endpoints=candidate.target_endpoints,
                        footprint=footprint,
                        rtp_list=rtp_list
                    )
                except Exception as e:
                    log_event("SCHEDULE_ERROR", f"Gagal menjalankan item antrean '{candidate.title}': {e}", level="ERROR")
            else:
                remaining_queue.append(candidate)

        self.playback_queue = remaining_queue

    def stop(self):
        """Menghentikan seluruh pemutaran audio di semua zona dan mengosongkan antrean."""
        with self._lock:
            for s in list(self.active_sessions.values()):
                s.stop_event.set()
                self._cleanup_session_procs(s)
            self.active_sessions.clear()
            self.playback_queue.clear()

            self.status = "IDLE"
            self.current_title = ""
            self.current_file = ""
            self.current_category = "biasa"
            self.started_at = 0.0
            self.elapsed = 0.0

            log_event("PLAYBACK_STOPPED", "Semua siaran dihentikan manual dan antrean dikosongkan")
            self.notify_listeners()

    def stop_session(self, session_id: str) -> bool:
        """Menghentikan satu sesi siaran tertentu dan memproses antrean yang tertunda."""
        with self._lock:
            if session_id in self.active_sessions:
                self._stop_session_locked(session_id, reason="STOPPED")
                self._process_queue_locked()
                self.notify_listeners()
                return True
            return False

    def remove_queued_item(self, queue_id: str) -> bool:
        """Menghapus item tertentu dari antrean jadwal."""
        with self._lock:
            before_len = len(self.playback_queue)
            self.playback_queue = [q for q in self.playback_queue if q.queue_id != queue_id]
            if len(self.playback_queue) < before_len:
                self.notify_listeners()
                return True
            return False

    def test_speaker_audio(self, ip: str, port: int = 5004):
        """Memutar jingle test pendek langsung ke satu IP speaker fisik tertentu via UDP RTP."""
        with self._lock:
            now = time.time()
            cooldown_key = f"{ip}:{port}"
            if cooldown_key in self._last_test_cooldown and (now - self._last_test_cooldown[cooldown_key] < 1.0):
                return
            self._last_test_cooldown[cooldown_key] = now

            chime_path = AUDIO_DIR / "test_chime.wav"
            if not chime_path.exists():
                raise FileNotFoundError("Berkas test_chime.wav tidak ditemukan")

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
            log_event("TEST_AUDIO", f"Mengirimkan uji suara UDP RTP ke {ip}:{port}")
        except Exception as e:
            log_event("TEST_AUDIO_ERROR", f"Gagal uji suara ke {ip}: {e}", level="ERROR")
            raise e


audio_engine = AudioEngine()
