import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.config import DB_PATH

def parse_groups(val: Any) -> List[str]:
    """Helper konversi string/list/json ke List[str] nama group yang unik dan bersih."""
    if not val:
        return []
    items = []
    if isinstance(val, (list, tuple, set)):
        for x in val:
            if isinstance(x, str):
                items.extend([p.strip() for p in x.split(",") if p.strip()])
            elif x:
                items.append(str(x).strip())
    elif isinstance(val, str):
        v = val.strip()
        if not v:
            return []
        if v.startswith("[") and v.endswith("]"):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    for x in parsed:
                        if isinstance(x, str):
                            items.extend([p.strip() for p in x.split(",") if p.strip()])
                        elif x:
                            items.append(str(x).strip())
                else:
                    items.extend([p.strip() for p in str(parsed).split(",") if p.strip()])
            except Exception:
                items.extend([x.strip() for x in v.strip("[]").split(",") if x.strip()])
        else:
            items.extend([x.strip() for x in v.split(",") if x.strip()])
    else:
        items.append(str(val).strip())

    seen = set()
    result = []
    for it in items:
        clean = it.strip('"\' ')
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Audio Files
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                format TEXT NOT NULL,
                duration REAL DEFAULT 0,
                size INTEGER DEFAULT 0,
                category TEXT DEFAULT 'biasa', -- 'biasa' | 'darurat'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Schedules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                audio_file_id INTEGER NOT NULL,
                schedule_type TEXT NOT NULL DEFAULT 'daily', -- daily, weekdays, interval, once
                time_str TEXT NOT NULL,                      -- HH:MM format
                days_of_week TEXT DEFAULT 'mon,tue,wed,thu,fri',
                interval_hours INTEGER DEFAULT 2,
                target_multicast INTEGER DEFAULT 1,
                target_local INTEGER DEFAULT 1,
                target_mode TEXT DEFAULT 'all',              -- all, zone, custom
                target_zone TEXT DEFAULT '',
                target_speakers TEXT DEFAULT '',             -- comma-separated IDs
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (audio_file_id) REFERENCES audio_files(id) ON DELETE CASCADE
            )
        """)

        # Speakers Table (Clean & Minimal: Name, IP, Port, Zone, Status & Telemetry)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip_address TEXT NOT NULL UNIQUE,
                port INTEGER DEFAULT 5004,
                zone TEXT DEFAULT 'Dermaga',
                status TEXT DEFAULT 'unknown',      -- 'online', 'offline', 'unknown'
                latency_ms INTEGER DEFAULT 0,
                last_online TIMESTAMP,
                last_checked TIMESTAMP,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Zones Table (Legacy Support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Groups Table (Multi-group support)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sync existing zones from speakers
        cursor.execute("""
            INSERT OR IGNORE INTO zones (name)
            SELECT DISTINCT zone FROM speakers WHERE zone IS NOT NULL AND TRIM(zone) != ''
        """)

        # Sync existing zones into groups
        cursor.execute("""
            INSERT OR IGNORE INTO groups (name, description, created_at)
            SELECT name, description, created_at FROM zones
        """)

        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Audit Logs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                level TEXT DEFAULT 'INFO',
                event TEXT NOT NULL,
                details TEXT
            )
        """)

        # Default Settings
        defaults = {
            "multicast_ip": "239.255.0.1",
            "multicast_port": "5004",
            "enable_multicast": "true",
            "enable_local": "false",
            "local_volume": "100"
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

        # Migrations for schedules table
        sched_cols = [c[1] for c in cursor.execute("PRAGMA table_info(schedules)").fetchall()]
        if "target_mode" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_mode TEXT DEFAULT 'all'")
        if "target_zone" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_zone TEXT DEFAULT ''")
        if "target_group" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_group TEXT DEFAULT ''")
        cursor.execute("""
            UPDATE schedules 
            SET target_group = target_zone 
            WHERE (target_group IS NULL OR target_group = '') AND target_zone IS NOT NULL AND target_zone != ''
        """)
        if "target_speaker_id" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_speaker_id INTEGER DEFAULT 0")
        if "target_speakers" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_speakers TEXT DEFAULT ''")

        # Migrations for audio_files table
        audio_cols = [c[1] for c in cursor.execute("PRAGMA table_info(audio_files)").fetchall()]
        if "category" not in audio_cols:
            cursor.execute("ALTER TABLE audio_files ADD COLUMN category TEXT DEFAULT 'biasa'")
        
        # Migrations for speakers table (Auto-discovery & Node Client Support)
        speaker_cols = [c[1] for c in cursor.execute("PRAGMA table_info(speakers)").fetchall()]
        if "node_id" not in speaker_cols:
            cursor.execute("ALTER TABLE speakers ADD COLUMN node_id TEXT")
        if "device_type" not in speaker_cols:
            cursor.execute("ALTER TABLE speakers ADD COLUMN device_type TEXT DEFAULT 'physical'")
        if "hostname" not in speaker_cols:
            cursor.execute("ALTER TABLE speakers ADD COLUMN hostname TEXT DEFAULT ''")
        if "groups" not in speaker_cols:
            cursor.execute("ALTER TABLE speakers ADD COLUMN groups TEXT DEFAULT '[]'")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_speakers_node_id ON speakers(node_id) WHERE node_id IS NOT NULL")

        # Pastikan kolom groups terisi dari zone jika ada speaker lama
        sp_rows = cursor.execute("SELECT id, zone, groups FROM speakers").fetchall()
        for sp in sp_rows:
            curr_grps = parse_groups(sp["groups"])
            if not curr_grps and sp["zone"] and sp["zone"].strip():
                new_grps = [sp["zone"].strip()]
                cursor.execute(
                    "UPDATE speakers SET groups = ? WHERE id = ?",
                    (json.dumps(new_grps), sp["id"])
                )

        # Ensure siren / ews files are tagged as 'darurat'
        cursor.execute("""
            UPDATE audio_files 
            SET category = 'darurat' 
            WHERE category IS NULL 
               OR category = '' 
               OR LOWER(filename) LIKE '%siren%' 
               OR LOWER(filename) LIKE '%sirine%' 
               OR LOWER(filename) LIKE '%ews%'
               OR LOWER(filename) LIKE '%emergency%'
               OR LOWER(filename) LIKE '%bahaya%'
               OR LOWER(filename) LIKE '%evakuasi%'
        """)

        # Pastikan tidak ada path Windows absolut yang tertinggal dari migrasi database
        cursor.execute("""
            UPDATE audio_files 
            SET file_path = filename 
            WHERE file_path LIKE 'C:%' OR file_path LIKE 'D:%' OR file_path LIKE '%\\%'
        """)

        conn.commit()

    # Pre-seed default speakers if table is empty
    seed_default_speakers()

def seed_default_speakers():
    """Tabel speaker dibiarkan bersih agar pengguna mendaftarkan IP speaker mandiri via Web Dashboard."""
    pass

def log_event(event: str, details: str = "", level: str = "INFO"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO logs (level, event, details) VALUES (?, ?, ?)",
            (level, event, details)
        )
        conn.commit()

def get_settings() -> Dict[str, str]:
    with get_db() as conn:
        return dict(conn.execute("SELECT key, value FROM settings").fetchall())

def update_settings(settings_dict: Dict[str, str]):
    with get_db() as conn:
        for k, v in settings_dict.items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, str(v)))
        conn.commit()

def get_all_speakers() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM speakers ORDER BY name ASC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["groups"] = parse_groups(d.get("groups") or d.get("zone"))
            d["zone"] = d["groups"][0] if d["groups"] else (d.get("zone") or "")
            result.append(d)
        return result

def get_speaker_by_id(speaker_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM speakers WHERE id = ?", (speaker_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["groups"] = parse_groups(d.get("groups") or d.get("zone"))
        d["zone"] = d["groups"][0] if d["groups"] else (d.get("zone") or "")
        return d

def create_speaker(
    name: str, 
    ip_address: str, 
    port: int = 5004, 
    groups: Any = None, 
    zone: str = "Kantor", 
    device_type: str = "physical"
) -> int:
    grp_list = parse_groups(groups) if groups is not None else parse_groups(zone)
    if not grp_list:
        grp_list = ["Kantor"]
    primary_group = grp_list[0]
    grp_json = json.dumps(grp_list)

    with get_db() as conn:
        cursor = conn.cursor()
        for g in grp_list:
            cursor.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (g,))
            cursor.execute("INSERT OR IGNORE INTO zones (name) VALUES (?)", (g,))
        cursor.execute("""
            INSERT INTO speakers (name, ip_address, port, zone, groups, status, device_type)
            VALUES (?, ?, ?, ?, ?, 'unknown', ?)
        """, (name, ip_address, port, primary_group, grp_json, device_type))
        conn.commit()
        return cursor.lastrowid

def update_speaker(
    speaker_id: int, 
    name: str, 
    ip_address: str, 
    port: int, 
    groups: Any = None, 
    zone: str = "Kantor", 
    enabled: int = 1
):
    grp_list = parse_groups(groups) if groups is not None else parse_groups(zone)
    if not grp_list:
        grp_list = ["Kantor"]
    primary_group = grp_list[0]
    grp_json = json.dumps(grp_list)

    with get_db() as conn:
        cursor = conn.cursor()
        for g in grp_list:
            cursor.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (g,))
            cursor.execute("INSERT OR IGNORE INTO zones (name) VALUES (?)", (g,))
        cursor.execute("""
            UPDATE speakers 
            SET name = ?, ip_address = ?, port = ?, zone = ?, groups = ?, enabled = ?
            WHERE id = ?
        """, (name, ip_address, port, primary_group, grp_json, enabled, speaker_id))
        conn.commit()

def delete_speaker(speaker_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM speakers WHERE id = ?", (speaker_id,))
        conn.commit()

def update_speaker_status(speaker_id: int, status: str, latency_ms: int = 0):
    with get_db() as conn:
        now = datetime.now().isoformat()
        if status == "online":
            conn.execute("""
                UPDATE speakers 
                SET status = ?, latency_ms = ?, last_online = ?, last_checked = ? 
                WHERE id = ?
            """, (status, latency_ms, now, now, speaker_id))
        else:
            conn.execute("""
                UPDATE speakers 
                SET status = ?, latency_ms = 0, last_checked = ? 
                WHERE id = ?
            """, (status, now, speaker_id))
        conn.commit()

# --- AUTO-DISCOVERY & DYNAMIC NODE HEARTBEAT ---
def upsert_node_heartbeat(
    node_id: str,
    device_name: str,
    zone: str = "Kantor",
    groups: Any = None,
    ip_address: str = "",
    port: int = 5004,
    hostname: str = "",
    force_update: bool = False
) -> Dict[str, Any]:
    """
    Mendaftarkan atau memperbarui status node client PC Windows secara dinamis.
    Mendukung multi-group, perubahan IP akibat DHCP tanpa benturan SQLite UNIQUE constraint.
    """
    node_id = (node_id or "").strip()
    if not node_id:
        raise ValueError("node_id tidak boleh kosong")

    grp_list = parse_groups(groups) if groups is not None else parse_groups(zone)
    if not grp_list:
        grp_list = ["Kantor"]
    primary_group = grp_list[0]
    grp_json = json.dumps(grp_list)

    device_name = (device_name or f"PC Audio ({hostname or node_id})").strip()
    now = datetime.now().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Pastikan setiap group terdaftar
        for g in grp_list:
            cursor.execute("INSERT OR IGNORE INTO groups (name) VALUES (?)", (g,))
            cursor.execute("INSERT OR IGNORE INTO zones (name) VALUES (?)", (g,))

        # 2. Tangani benturan IP jika IP ini pernah dipegang oleh record lain
        cursor.execute(
            "SELECT id, node_id, name FROM speakers WHERE ip_address = ? AND (node_id IS NULL OR node_id != ?)",
            (ip_address, node_id)
        )
        conflicts = cursor.fetchall()
        for conf in conflicts:
            c_id = conf["id"]
            cursor.execute(
                "UPDATE speakers SET ip_address = ?, status = 'offline' WHERE id = ?",
                (f"pending-{c_id}-{int(datetime.now().timestamp())}", c_id)
            )

        # 3. Cek apakah node_id sudah ada di database
        cursor.execute("SELECT * FROM speakers WHERE node_id = ?", (node_id,))
        existing = cursor.fetchone()

        # Deteksi jika ada 2 PC berbeda yang mengirim node_id yang sama (misal hasil cloning/copy folder).
        # Hanya dianggap clone jika hostname BERBEDA. Hostname sama + IP berubah = DHCP/WiFi roaming -> cukup update IP.
        if (
            existing
            and existing["ip_address"] != ip_address
            and hostname
            and existing["hostname"]
            and existing["hostname"] != hostname
        ):
            is_cloned_node = False
            if existing["last_online"]:
                try:
                    delta = (datetime.now() - datetime.fromisoformat(existing["last_online"])).total_seconds()
                    if delta <= 90:
                        is_cloned_node = True
                except Exception:
                    is_cloned_node = True
            else:
                is_cloned_node = True

            if is_cloned_node:
                # Pisahkan node_id untuk PC ini agar keduanya terdaftar terpisah sebagai speaker mandiri
                node_id = f"{node_id}_{ip_address.replace('.', '_')}"
                cursor.execute("SELECT * FROM speakers WHERE node_id = ?", (node_id,))
                existing = cursor.fetchone()

        if existing:
            speaker_id = existing["id"]
            if force_update:
                cursor.execute("""
                    UPDATE speakers
                    SET name = ?,
                        ip_address = ?,
                        port = ?,
                        zone = ?,
                        groups = ?,
                        hostname = ?,
                        status = 'online',
                        latency_ms = 1,
                        last_online = ?,
                        last_checked = ?,
                        device_type = 'node'
                    WHERE id = ?
                """, (device_name, ip_address, port, primary_group, grp_json, hostname, now, now, speaker_id))
            else:
                cursor.execute("""
                    UPDATE speakers
                    SET ip_address = ?,
                        port = ?,
                        hostname = ?,
                        status = 'online',
                        latency_ms = 1,
                        last_online = ?,
                        last_checked = ?,
                        device_type = 'node'
                    WHERE id = ?
                """, (ip_address, port, hostname, now, now, speaker_id))
        else:
            cursor.execute("""
                INSERT INTO speakers (
                    name, ip_address, port, zone, groups, status, latency_ms,
                    last_online, last_checked, enabled, node_id, device_type, hostname
                )
                VALUES (?, ?, ?, ?, ?, 'online', 1, ?, ?, 1, ?, 'node', ?)
            """, (device_name, ip_address, port, primary_group, grp_json, now, now, node_id, hostname))
            speaker_id = cursor.lastrowid

        conn.commit()

        cursor.execute("SELECT * FROM speakers WHERE id = ?", (speaker_id,))
        row = cursor.fetchone()
        if not row:
            return {}
        d = dict(row)
        d["groups"] = parse_groups(d.get("groups") or d.get("zone"))
        d["zone"] = d["groups"][0] if d["groups"] else (d.get("zone") or "")
        return d

def mark_stale_nodes_offline(timeout_seconds: int = 45) -> int:
    """Menandai node PC client yang tidak mengirim heartbeat melebihi timeout menjadi offline."""
    now = datetime.now()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, last_online FROM speakers WHERE device_type = 'node' AND status = 'online'")
        rows = cursor.fetchall()
        stale_ids = []
        for r in rows:
            last_online_str = r["last_online"]
            if not last_online_str:
                stale_ids.append(r["id"])
                continue
            try:
                last_dt = datetime.fromisoformat(last_online_str)
                if (now - last_dt).total_seconds() > timeout_seconds:
                    stale_ids.append(r["id"])
            except Exception:
                stale_ids.append(r["id"])

        if stale_ids:
            placeholders = ",".join(["?"] * len(stale_ids))
            cursor.execute(f"UPDATE speakers SET status = 'offline', latency_ms = 0 WHERE id IN ({placeholders})", stale_ids)
            conn.commit()
            return len(stale_ids)
        return 0

# --- GROUPS & ZONES CRUD ---
def get_all_groups() -> List[Dict[str, Any]]:
    with get_db() as conn:
        groups_rows = conn.execute("SELECT id, name, description, created_at FROM groups ORDER BY name ASC").fetchall()
        speakers_rows = conn.execute("SELECT id, groups, zone FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
        
        counts = {}
        for sp in speakers_rows:
            sp_groups = parse_groups(sp["groups"] or sp["zone"])
            for g in sp_groups:
                counts[g] = counts.get(g, 0) + 1

        result = []
        for gr in groups_rows:
            d = dict(gr)
            d["speaker_count"] = counts.get(d["name"], 0)
            result.append(d)
        return result

def create_group(name: str, description: str = "") -> int:
    name = name.strip()
    if not name:
        raise ValueError("Nama group tidak boleh kosong")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO groups (name, description) VALUES (?, ?)", (name, description or ""))
        cursor.execute("INSERT OR IGNORE INTO zones (name, description) VALUES (?, ?)", (name, description or ""))
        conn.commit()
        return cursor.lastrowid

def update_group(old_name: str, new_name: str, description: Optional[str] = None):
    old_name = old_name.strip()
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Nama group baru tidak boleh kosong")
    with get_db() as conn:
        if description is not None:
            conn.execute("UPDATE groups SET name = ?, description = ? WHERE name = ?", (new_name, description, old_name))
            conn.execute("UPDATE zones SET name = ?, description = ? WHERE name = ?", (new_name, description, old_name))
        else:
            conn.execute("UPDATE groups SET name = ? WHERE name = ?", (new_name, old_name))
            conn.execute("UPDATE zones SET name = ? WHERE name = ?", (new_name, old_name))

        # Update speakers who have this group in their groups list
        speakers = conn.execute("SELECT id, groups, zone FROM speakers").fetchall()
        for sp in speakers:
            sp_groups = parse_groups(sp["groups"] or sp["zone"])
            if old_name in sp_groups:
                updated_groups = [new_name if g == old_name else g for g in sp_groups]
                seen = set()
                deduped = [x for x in updated_groups if not (x in seen or seen.add(x))]
                conn.execute(
                    "UPDATE speakers SET groups = ?, zone = ? WHERE id = ?",
                    (json.dumps(deduped), deduped[0] if deduped else "", sp["id"])
                )

        conn.execute("UPDATE schedules SET target_group = ? WHERE target_group = ?", (new_name, old_name))
        conn.execute("UPDATE schedules SET target_zone = ? WHERE target_zone = ?", (new_name, old_name))
        conn.commit()

def delete_group(name: str):
    name = name.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM groups WHERE name = ?", (name,))
        cursor.execute("DELETE FROM zones WHERE name = ?", (name,))

        speakers = cursor.execute("SELECT id, groups, zone FROM speakers").fetchall()
        for sp in speakers:
            sp_groups = parse_groups(sp["groups"] or sp["zone"])
            if name in sp_groups:
                updated_groups = [g for g in sp_groups if g != name]
                primary = updated_groups[0] if updated_groups else "Kantor"
                cursor.execute(
                    "UPDATE speakers SET groups = ?, zone = ? WHERE id = ?",
                    (json.dumps(updated_groups), primary, sp["id"])
                )
        conn.commit()

# Legacy Zone Aliases (Fully backward-compatible)
def get_all_zones() -> List[Dict[str, Any]]:
    return get_all_groups()

def create_zone(name: str, description: str = "") -> int:
    return create_group(name, description)

def update_zone(old_name: str, new_name: str, description: Optional[str] = None):
    return update_group(old_name, new_name, description)

def delete_zone(name: str):
    return delete_group(name)
