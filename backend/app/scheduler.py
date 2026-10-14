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

        raw_groups = []
        if tgroup:
            raw_groups.extend([g.strip() for g in tgroup.replace("[","").replace("]","").replace('"','').split(",") if g.strip()])
        target_groups = list(dict.fromkeys(raw_groups))

        raw_ids = []
        if tspk_id:
            raw_ids.append(int(tspk_id))
        tspk_ids_str = row["target_speakers"] if "target_speakers" in row.keys() else ""
        if tspk_ids_str:
            for x in str(tspk_ids_str).split(","):
                if x.strip().isdigit():
                    raw_ids.append(int(x.strip()))
        target_speaker_ids = list(dict.fromkeys(raw_ids))

        is_all_mode = (tmode == "all" and not target_groups and not target_speaker_ids)

        if not is_all_mode and (target_groups or target_speaker_ids):
            matching_dict = {}
            with get_db() as conn:
                all_spk_rows = conn.execute("SELECT id, name, ip_address, port, groups, zone FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
                if target_groups:
                    for r in all_spk_rows:
                        grps = parse_groups(r["groups"] or r["zone"])
                        if any(tg.lower() in [x.lower() for x in grps] or (r["zone"] and r["zone"].lower() == tg.lower()) for tg in target_groups):
                            matching_dict[r["id"]] = r
                if target_speaker_ids:
                    for r in all_spk_rows:
                        if r["id"] in target_speaker_ids:
                            matching_dict[r["id"]] = r

            if matching_dict:
                target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in matching_dict.values()]
                desc_parts = []
                if target_groups:
                    desc_parts.append(f"{len(target_groups)} Group ({', '.join(target_groups)})")
                if target_speaker_ids:
                    spk_names = [r["name"] for r in matching_dict.values() if r["id"] in target_speaker_ids]
                    if len(target_speaker_ids) == 1 and spk_names:
                        desc_parts.append(f"Speaker {spk_names[0]}")
                    else:
                        desc_parts.append(f"{len(target_speaker_ids)} Speaker")
                target_desc = " + ".join(desc_parts) + f" ({len(target_endpoints)} Speaker)"
            else:
                is_all_mode = True

        if is_all_mode:
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
