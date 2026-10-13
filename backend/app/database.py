import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.config import DB_PATH

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

        # Zones Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
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
        cursor.execute("""
            INSERT OR IGNORE INTO zones (name)
            VALUES ('Dermaga'), ('Lapangan & Gudang'), ('Kantor & Kontrol')
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
        if "target_speaker_id" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_speaker_id INTEGER DEFAULT 0")
        if "target_speakers" not in sched_cols:
            cursor.execute("ALTER TABLE schedules ADD COLUMN target_speakers TEXT DEFAULT ''")
        # Migrations for audio_files table
        audio_cols = [c[1] for c in cursor.execute("PRAGMA table_info(audio_files)").fetchall()]
        if "category" not in audio_cols:
            cursor.execute("ALTER TABLE audio_files ADD COLUMN category TEXT DEFAULT 'biasa'")
        
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
        rows = conn.execute("SELECT * FROM speakers ORDER BY zone ASC, name ASC").fetchall()
        return [dict(r) for r in rows]

def get_speaker_by_id(speaker_id: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM speakers WHERE id = ?", (speaker_id,)).fetchone()
        return dict(row) if row else None

def create_speaker(name: str, ip_address: str, port: int = 5004, zone: str = "Dermaga") -> int:
    zone = (zone or "Dermaga").strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO zones (name) VALUES (?)", (zone,))
        cursor.execute("""
            INSERT INTO speakers (name, ip_address, port, zone, status)
            VALUES (?, ?, ?, ?, 'unknown')
        """, (name, ip_address, port, zone))
        conn.commit()
        return cursor.lastrowid

def update_speaker(speaker_id: int, name: str, ip_address: str, port: int, zone: str, enabled: int = 1):
    zone = (zone or "Dermaga").strip()
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO zones (name) VALUES (?)", (zone,))
        conn.execute("""
            UPDATE speakers 
            SET name = ?, ip_address = ?, port = ?, zone = ?, enabled = ?
            WHERE id = ?
        """, (name, ip_address, port, zone, enabled, speaker_id))
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

# --- ZONES CRUD ---
def get_all_zones() -> List[Dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT z.id, z.name, z.description, z.created_at,
                   COUNT(s.id) as speaker_count
            FROM zones z
            LEFT JOIN speakers s ON s.zone = z.name
            GROUP BY z.id, z.name
            ORDER BY z.name ASC
        """).fetchall()
        return [dict(r) for r in rows]

def create_zone(name: str, description: str = "") -> int:
    name = name.strip()
    if not name:
        raise ValueError("Nama zona tidak boleh kosong")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO zones (name, description) VALUES (?, ?)", (name, description or ""))
        conn.commit()
        return cursor.lastrowid

def update_zone(old_name: str, new_name: str, description: Optional[str] = None):
    old_name = old_name.strip()
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Nama zona baru tidak boleh kosong")
    with get_db() as conn:
        if description is not None:
            conn.execute("UPDATE zones SET name = ?, description = ? WHERE name = ?", (new_name, description, old_name))
        else:
            conn.execute("UPDATE zones SET name = ? WHERE name = ?", (new_name, old_name))
        conn.execute("UPDATE speakers SET zone = ? WHERE zone = ?", (new_name, old_name))
        conn.execute("UPDATE schedules SET target_zone = ? WHERE target_zone = ?", (new_name, old_name))
        conn.commit()

def delete_zone(name: str):
    name = name.strip()
    with get_db() as conn:
        conn.execute("DELETE FROM zones WHERE name = ?", (name,))
        # Set speaker di zona ini ke 'Umum'
        conn.execute("INSERT OR IGNORE INTO zones (name) VALUES ('Umum')")
        conn.execute("UPDATE speakers SET zone = 'Umum' WHERE zone = ?", (name,))
        conn.execute("UPDATE schedules SET target_zone = 'Umum' WHERE target_zone = ?", (name,))
        conn.commit()
