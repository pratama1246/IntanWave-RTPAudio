import logging
import zoneinfo
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.database import get_db, log_event, get_settings, parse_groups
from app.config import DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT, AUDIO_DIR
from app.audio_engine import audio_engine

logger = logging.getLogger("pa_scheduler")
JAKARTA_TZ = zoneinfo.ZoneInfo("Asia/Jakarta")
scheduler = AsyncIOScheduler(timezone=JAKARTA_TZ)

async def trigger_schedule_job(schedule_id: int):
    """Fungsi yang dipanggil saat alarm scheduler jatuh tempo."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT s.*, a.file_path, a.display_name, a.filename, a.category 
            FROM schedules s
            JOIN audio_files a ON s.audio_file_id = a.id
            WHERE s.id = ? AND s.enabled = 1
        """, (schedule_id,)).fetchone()

    if not row:
        return

    # Pastikan file path valid lintas platform (Linux Docker vs Windows Host)
    fpath = AUDIO_DIR / row["filename"]
    if not fpath.exists():
        stored_path = Path(row["file_path"])
        if stored_path.exists():
            fpath = stored_path
        else:
            log_event("SCHEDULE_ERROR", f"Berkas fisik '{row['filename']}' tidak ditemukan di storage", level="ERROR")
            return

    log_event("SCHEDULE_TRIGGERED", f"Memutar jadwal otomatis: '{row['name']}' ({row['display_name']})")
    try:
        tmode = row["target_mode"] if "target_mode" in row.keys() else "all"
        tgroup = row["target_group"] if "target_group" in row.keys() else (row["target_zone"] if "target_zone" in row.keys() else "")
        tspk_id = row["target_speaker_id"] if "target_speaker_id" in row.keys() else 0

        target_endpoints = None
        target_desc = "Semua Speaker"

        if tmode in ("group", "zone") and tgroup:
            with get_db() as conn:
                sp_rows = conn.execute("SELECT id, ip_address, port, groups, zone FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
                target_groups = [g.strip() for g in tgroup.replace("[","").replace("]","").replace('"','').split(",") if g.strip()]
                matching_rows = []
                for r in sp_rows:
                    grps = parse_groups(r["groups"] or r["zone"])
                    if any(tg.lower() in [x.lower() for x in grps] or (r["zone"] and r["zone"].lower() == tg.lower()) for tg in target_groups):
                        matching_rows.append(r)
                if matching_rows:
                    target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in matching_rows]
                    target_desc = f"Group {', '.join(target_groups)} ({len(target_endpoints)} Speaker)"
        elif tmode == "speaker" and tspk_id:
            with get_db() as conn:
                sp_row = conn.execute("SELECT ip_address, port, name FROM speakers WHERE id = ? AND enabled = 1 AND ip_address NOT LIKE 'pending-%'", (tspk_id,)).fetchone()
                if sp_row:
                    target_endpoints = [f"{sp_row['ip_address']}:{sp_row['port']}"]
                    target_desc = f"Speaker {sp_row['name']}"
        else:
            with get_db() as conn:
                sp_rows = conn.execute("SELECT ip_address, port FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
                settings = get_settings()
                mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
                mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
                target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in sp_rows]
                target_endpoints.append(f"{mc_ip}:{mc_port}")
                target_desc = f"Semua Speaker ({len(sp_rows)} Speaker & Multicast)"

        cat = row["category"] if "category" in row.keys() else "biasa"
        audio_engine.play(
            file_path=str(fpath.resolve()),
            title=f"[Jadwal] {row['name']}",
            enable_multicast=bool(row["target_multicast"]),
            enable_local=bool(row["target_local"]),
            target_endpoints=target_endpoints,
            target_desc=target_desc,
            category=cat
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

    total_jobs = 0
    for s in schedules:
        stype = s["schedule_type"]
        
        # Mode interval tidak memerlukan multi-jam
        if stype == "interval":
            hours = s["interval_hours"] or 2
            trigger = IntervalTrigger(hours=hours, timezone=JAKARTA_TZ)
            scheduler.add_job(
                trigger_schedule_job,
                trigger=trigger,
                args=[s["id"]],
                id=f"schedule_{s['id']}_interval",
                replace_existing=True
            )
            total_jobs += 1
            continue

        # Mendukung multi-time (misal: "08:00, 11:00, 15:00")
        raw_times = [t.strip() for t in (s["time_str"] or "08:00").split(",") if t.strip()]
        if not raw_times:
            raw_times = ["08:00"]

        for idx, t_str in enumerate(raw_times):
            job_id = f"schedule_{s['id']}_{idx}"
            time_parts = t_str.split(":")
            try:
                hour = int(time_parts[0]) if len(time_parts) > 0 else 0
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            except ValueError:
                continue

            trigger = None
            if stype == "daily":
                trigger = CronTrigger(hour=hour, minute=minute, timezone=JAKARTA_TZ)
            elif stype in ("weekdays", "custom", "days"):
                dow = s["days_of_week"] if "days_of_week" in s.keys() and s["days_of_week"] else None
                days = dow.strip() if dow and dow.strip() else ("mon-fri" if stype == "weekdays" else "*")
                trigger = CronTrigger(day_of_week=days, hour=hour, minute=minute, timezone=JAKARTA_TZ)
            elif stype == "once":
                trigger = CronTrigger(hour=hour, minute=minute, timezone=JAKARTA_TZ)

            if trigger:
                scheduler.add_job(
                    trigger_schedule_job,
                    trigger=trigger,
                    args=[s["id"]],
                    id=job_id,
                    replace_existing=True
                )
                total_jobs += 1

    log_event("SCHEDULER_RELOADED", f"{len(schedules)} jadwal aktif dimuat ({total_jobs} trigger waktu terdaftar).")
