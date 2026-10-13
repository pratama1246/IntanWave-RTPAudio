import asyncio
import re
import sys
from typing import Dict, Any, List, Optional, Callable
from app.database import get_all_speakers, update_speaker_status, get_speaker_by_id

LATENCY_REGEX = re.compile(r"(?:time|waktu)[=<]\s*(\d+)\s*ms", re.IGNORECASE)

async def ping_ip(ip: str, timeout_ms: int = 1000) -> tuple[bool, int]:
    """
    Melakukan ICMP ping asinkron ke IP tujuan.
    Mengembalikan tuple: (is_online: bool, latency_ms: int).
    """
    ip = ip.strip()
    if not ip:
        return False, 0

    if sys.platform == "win32":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), ip]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_ms / 1000.0 + 1.5)
        text = stdout.decode("latin-1", errors="ignore")

        # Cek apakah online: terdapat TTL= atau bytes=
        text_lower = text.lower()
        is_online = ("ttl=" in text_lower) or ("bytes from" in text_lower) or ("bytes=" in text_lower)

        latency = 0
        if is_online:
            match = LATENCY_REGEX.search(text)
            if match:
                latency = int(match.group(1))
            else:
                latency = 1  # Default fallback jika sub-milidetik (<1ms)

        return is_online, latency
    except Exception:
        return False, 0

async def check_speaker(speaker: Dict[str, Any]) -> Dict[str, Any]:
    """Cek 1 speaker dan update database."""
    # Untuk node PC Windows client, status online ditentukan oleh penerimaan heartbeat (timeout 45 detik)
    # Hal ini mencegah salah deteksi 'offline' akibat Windows Firewall yang memblokir ICMP echo request (ping)
    if speaker.get("device_type") == "node":
        last_online_str = speaker.get("last_online")
        is_online = False
        if last_online_str:
            try:
                from datetime import datetime
                last_dt = datetime.fromisoformat(last_online_str)
                is_online = (datetime.now() - last_dt).total_seconds() <= 45
            except Exception:
                pass
        status = "online" if is_online else "offline"
        latency = 1 if is_online else 0
        update_speaker_status(speaker["id"], status, latency)

        speaker_copy = dict(speaker)
        speaker_copy["status"] = status
        speaker_copy["latency_ms"] = latency
        return speaker_copy

    ip = speaker.get("ip_address", "")
    if ip.startswith("pending-"):
        status = "offline"
        latency = 0
    else:
        is_online, latency = await ping_ip(ip)
        status = "online" if is_online else "offline"

    update_speaker_status(speaker["id"], status, latency)

    speaker_copy = dict(speaker)
    speaker_copy["status"] = status
    speaker_copy["latency_ms"] = latency
    return speaker_copy

async def scan_all_speakers_parallel() -> List[Dict[str, Any]]:
    """Scan semua speaker secara paralel via asyncio.gather."""
    speakers = get_all_speakers()
    tasks = [check_speaker(s) for s in speakers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    updated_list = []
    for r in results:
        if isinstance(r, dict):
            updated_list.append(r)

    return get_all_speakers()

class PingMonitor:
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.broadcast_callback: Optional[Callable[[dict], Any]] = None

    def start(self, broadcast_callback=None, interval_seconds=30):
        self.running = True
        self.broadcast_callback = broadcast_callback
        self.task = asyncio.create_task(self._monitor_loop(interval_seconds))

    def stop(self):
        self.running = False
        if self.task and not self.task.done():
            self.task.cancel()

    async def _monitor_loop(self, interval_seconds: int):
        while self.running:
            try:
                speakers = await scan_all_speakers_parallel()
                if self.broadcast_callback:
                    await self.broadcast_callback({
                        "type": "speakers_update",
                        "speakers": speakers
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[PingMonitor] Error during scan: {e}")

            await asyncio.sleep(interval_seconds)

ping_monitor = PingMonitor()
