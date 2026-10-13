import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.database import get_db, log_event, get_settings
from app.config import DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT
from app.audio_engine import audio_engine

logger = logging.getLogger("pa_scheduler")
scheduler = AsyncIOScheduler()

async def trigger_schedule_job(schedule_id: int):
    """Fungsi yang dipanggil saat alarm scheduler jatuh tempo."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT s.*, a.file_path, a.display_name 
            FROM schedules s
            JOIN audio_files a ON s.audio_file_id = a.id
            WHERE s.id = ? AND s.enabled = 1
        """, (schedule_id,)).fetchone()

    if not row:
        return

    log_event("SCHEDULE_TRIGGERED", f"Memutar jadwal otomatis: '{row['name']}' ({row['display_name']})")
    try:
        tmode = row["target_mode"] if "target_mode" in row.keys() else "all"
        tzone = row["target_zone"] if "target_zone" in row.keys() else ""
        tspk_id = row["target_speaker_id"] if "target_speaker_id" in row.keys() else 0

        target_endpoints = None
        target_desc = "Semua Speaker"

        if tmode == "zone" and tzone:
            with get_db() as conn:
                sp_rows = conn.execute("SELECT ip_address, port FROM speakers WHERE zone = ? AND enabled = 1", (tzone,)).fetchall()
                if sp_rows:
                    target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in sp_rows]
                    target_desc = f"Zona {tzone} ({len(target_endpoints)} Speaker)"
        elif tmode == "speaker" and tspk_id:
            with get_db() as conn:
                sp_row = conn.execute("SELECT ip_address, port, name FROM speakers WHERE id = ? AND enabled = 1", (tspk_id,)).fetchone()
                if sp_row:
                    target_endpoints = [f"{sp_row['ip_address']}:{sp_row['port']}"]
                    target_desc = f"Speaker {sp_row['name']}"
        else:
            with get_db() as conn:
                sp_rows = conn.execute("SELECT ip_address, port FROM speakers WHERE enabled = 1").fetchall()
                settings = get_settings()
                mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
                mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
                target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in sp_rows]
                target_endpoints.append(f"{mc_ip}:{mc_port}")
                target_desc = f"Semua Speaker ({len(sp_rows)} Speaker & Multicast)"

        audio_engine.play(
            file_path=row["file_path"],
            title=f"[Jadwal] {row['name']}",
            enable_multicast=bool(row["target_multicast"]),
            enable_local=bool(row["target_local"]),
            target_endpoints=target_endpoints,
            target_desc=target_desc
        )
    except Exception as e:
        log_event("SCHEDULE_ERROR", f"Gagal mengeksekusi jadwal '{row['name']}': {e}", level="ERROR")

def reload_schedules():
    """Membaca ulang semua jadwal dari database dan mendaftarkan ke APScheduler."""
    scheduler.remove_all_jobs()
    
    with get_db() as conn:
        schedules = conn.execute("""
            SELECT * FROM schedules WHERE enabled = 1
        """).fetchall()

    for s in schedules:
        job_id = f"schedule_{s['id']}"
        time_parts = s["time_str"].split(":")
        hour = int(time_parts[0]) if len(time_parts) > 0 else 0
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        trigger = None
        stype = s["schedule_type"]

        if stype == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
        elif stype in ("weekdays", "custom", "days"):
            dow = s["days_of_week"] if "days_of_week" in s.keys() and s["days_of_week"] else None
            days = dow.strip() if dow and dow.strip() else ("mon-fri" if stype == "weekdays" else "*")
            trigger = CronTrigger(day_of_week=days, hour=hour, minute=minute)
        elif stype == "interval":
            hours = s["interval_hours"] or 2
            trigger = IntervalTrigger(hours=hours)
        elif stype == "once":
            trigger = CronTrigger(hour=hour, minute=minute)

        if trigger:
            scheduler.add_job(
                trigger_schedule_job,
                trigger=trigger,
                args=[s["id"]],
                id=job_id,
                replace_existing=True
            )

    log_event("SCHEDULER_RELOADED", f"{len(schedules)} jadwal aktif dimuat ke scheduler.")
