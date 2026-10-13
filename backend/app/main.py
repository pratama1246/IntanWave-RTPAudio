import asyncio
import os
import shutil
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import AUDIO_DIR, BASE_DIR, DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT
from app.database import (
    init_db, get_db, log_event, get_settings, update_settings,
    get_all_speakers, get_speaker_by_id, create_speaker, update_speaker, 
    delete_speaker, update_speaker_status,
    get_all_zones, create_zone, update_zone, delete_zone
)
from app.audio_engine import audio_engine
from app.scheduler import scheduler, reload_schedules
from app.ping_service import ping_ip, scan_all_speakers_parallel, ping_monitor

FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist")))


# Websocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Kirim status awal playback
        await websocket.send_json(audio_engine.get_status())
        # Kirim status awal seluruh speaker dan zona
        try:
            speakers = get_all_speakers()
            await websocket.send_json({"type": "speakers_update", "speakers": speakers})
        except Exception:
            pass
        try:
            zones = get_all_zones()
            await websocket.send_json({"type": "zones_update", "zones": zones})
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for conn in list(self.active_connections):
            try:
                await conn.send_json(data)
            except Exception:
                self.disconnect(conn)

manager = ConnectionManager()
loop = None

def on_engine_update(status_dict: dict):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast(status_dict), loop)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop
    loop = asyncio.get_running_loop()
    
    # 1. Init DB
    init_db()
    
    # 2. Sync audio files in storage/audio
    sync_audio_files_to_db()

    # 3. Register audio engine listener
    audio_engine.add_listener(on_engine_update)

    # 4. Start scheduler
    scheduler.start()
    reload_schedules()

    # 5. Start background ping monitor (scan setiap 30 detik)
    ping_monitor.start(broadcast_callback=manager.broadcast, interval_seconds=30)
    
    log_event("SERVER_START", "Server PA Audio Console berhasil dijalankan.")

    yield

    # Shutdown
    ping_monitor.stop()
    scheduler.shutdown()
    audio_engine.stop()
    log_event("SERVER_SHUTDOWN", "Server PA Audio dihentikan.")

app = FastAPI(title="GoPA Audio System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sync_audio_files_to_db():
    """Memindai folder audio dan mendaftarkan file yang belum tercatat."""
    valid_exts = {".wav", ".mp3", ".ogg", ".flac"}
    with get_db() as conn:
        for f in AUDIO_DIR.glob("*"):
            if f.suffix.lower() in valid_exts and f.is_file():
                existing = conn.execute("SELECT id FROM audio_files WHERE filename = ?", (f.name,)).fetchone()
                if not existing:
                    duration = audio_engine.get_audio_duration(str(f))
                    name = f.stem.replace("_", " ").title()
                    lname = f.name.lower()
                    cat = "darurat" if any(k in lname for k in ["siren", "sirine", "ews", "emergency", "bahaya", "evakuasi"]) else "biasa"
                    conn.execute("""
                        INSERT INTO audio_files (filename, display_name, file_path, format, duration, size, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (f.name, name, str(f.resolve()), f.suffix.lower()[1:], duration, f.stat().st_size, cat))
        conn.commit()

# --- WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- AUDIO LIBRARY ENDPOINTS ---
class AudioUpdateRequest(BaseModel):
    category: Optional[str] = None
    display_name: Optional[str] = None

@app.get("/api/audio")
def list_audio():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM audio_files ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/api/audio/upload")
async def upload_audio(
    file: UploadFile = File(...), 
    display_name: Optional[str] = Form(None),
    category: Optional[str] = Form("biasa")
):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".wav", ".mp3", ".ogg", ".flac"}:
        raise HTTPException(status_code=400, detail="Format file harus MP3, WAV, OGG, atau FLAC")

    save_path = AUDIO_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    duration = audio_engine.get_audio_duration(str(save_path))
    disp_name = display_name if display_name else Path(file.filename).stem.replace("_", " ").title()
    size = save_path.stat().st_size
    cat = (category or "biasa").strip().lower()
    if cat not in ("biasa", "darurat"):
        cat = "biasa"

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO audio_files (filename, display_name, file_path, format, duration, size, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file.filename, disp_name, str(save_path.resolve()), ext[1:], duration, size, cat))
        conn.commit()

    log_event("AUDIO_UPLOADED", f"Berhasil mengunggah '{disp_name}' [{cat.upper()}] ({file.filename})")
    return {"message": "Upload berhasil", "filename": file.filename, "category": cat}

@app.patch("/api/audio/{audio_id}")
def update_audio_info(audio_id: int, req: AudioUpdateRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")
        
        updates = []
        params = []
        if req.category is not None:
            cat = req.category.strip().lower()
            if cat in ("biasa", "darurat"):
                updates.append("category = ?")
                params.append(cat)
        if req.display_name is not None and req.display_name.strip():
            updates.append("display_name = ?")
            params.append(req.display_name.strip())
            
        if updates:
            params.append(audio_id)
            conn.execute(f"UPDATE audio_files SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            log_event("AUDIO_UPDATED", f"Memperbarui audio ID {audio_id}: {req.category or ''}")
            
    return {"message": "Audio berhasil diperbarui"}

@app.delete("/api/audio/{audio_id}")
def delete_audio(audio_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")

        fpath = Path(row["file_path"])
        if fpath.exists():
            try:
                fpath.unlink()
            except Exception:
                pass

        conn.execute("DELETE FROM audio_files WHERE id = ?", (audio_id,))
        conn.commit()

    log_event("AUDIO_DELETED", f"Menghapus audio: '{row['display_name']}'")
    return {"message": "Audio berhasil dihapus"}

@app.get("/api/audio/{audio_id}/stream")
def stream_audio(audio_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")
        fpath = Path(row["file_path"])
        if not fpath.exists():
            raise HTTPException(status_code=404, detail="Berkas fisik tidak ditemukan")
        fmt = row["format"].lower()
        media_type = "audio/mpeg" if fmt == "mp3" else f"audio/{fmt}"
        return FileResponse(str(fpath), media_type=media_type)

@app.get("/api/audio/stream-file/{filename}")
def stream_audio_by_filename(filename: str):
    fpath = AUDIO_DIR / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Berkas fisik tidak ditemukan")
    ext = fpath.suffix.lower()[1:]
    media_type = "audio/mpeg" if ext == "mp3" else f"audio/{ext}"
    return FileResponse(str(fpath), media_type=media_type)

# --- PLAYBACK CONTROLS ---
class PlayRequest(BaseModel):
    audio_id: Optional[int] = None
    filename: Optional[str] = None
    enable_multicast: Optional[bool] = None
    enable_local: Optional[bool] = None
    target_mode: Optional[str] = "all"  # 'all', 'zone', 'speaker', 'custom'
    target_zone: Optional[str] = None
    speaker_id: Optional[int] = None
    speaker_ids: Optional[List[int]] = None

@app.post("/api/play")
def play_audio(req: PlayRequest):
    with get_db() as conn:
        if req.audio_id:
            row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (req.audio_id,)).fetchone()
        elif req.filename:
            row = conn.execute("SELECT * FROM audio_files WHERE filename = ?", (req.filename,)).fetchone()
        else:
            raise HTTPException(status_code=400, detail="audio_id atau filename harus disertakan")

    if not row:
        raise HTTPException(status_code=404, detail="File audio tidak ditemukan")

    target_endpoints = None
    target_desc = "Semua Speaker"

    if req.target_mode == "zone" and req.target_zone:
        with get_db() as conn:
            rows = conn.execute("SELECT ip_address, port FROM speakers WHERE zone = ? AND enabled = 1", (req.target_zone,)).fetchall()
            if rows:
                target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in rows]
                target_desc = f"Zona {req.target_zone} ({len(target_endpoints)} Speaker)"
    elif req.target_mode == "speaker" and req.speaker_id:
        with get_db() as conn:
            sp = conn.execute("SELECT ip_address, port, name FROM speakers WHERE id = ? AND enabled = 1", (req.speaker_id,)).fetchone()
            if sp:
                target_endpoints = [f"{sp['ip_address']}:{sp['port']}"]
                target_desc = f"Speaker {sp['name']}"
    elif req.target_mode == "custom" and req.speaker_ids:
        with get_db() as conn:
            placeholders = ",".join(["?"] * len(req.speaker_ids))
            rows = conn.execute(f"SELECT ip_address, port FROM speakers WHERE id IN ({placeholders}) AND enabled = 1", req.speaker_ids).fetchall()
            if rows:
                target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in rows]
                target_desc = f"{len(target_endpoints)} Speaker Terpilih"
    else:
        # Mode "all" (Semua Speaker): Kirim ke seluruh IP speaker fisik terdaftar + Multicast
        with get_db() as conn:
            rows = conn.execute("SELECT ip_address, port FROM speakers WHERE enabled = 1").fetchall()
            settings = get_settings()
            mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
            mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
            target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in rows]
            target_endpoints.append(f"{mc_ip}:{mc_port}")
            target_desc = f"Semua Speaker ({len(rows)} Speaker & Multicast)"

    try:
        audio_engine.play(
            file_path=row["file_path"],
            title=row["display_name"],
            enable_multicast=req.enable_multicast,
            enable_local=req.enable_local,
            target_endpoints=target_endpoints,
            target_desc=target_desc
        )
        return {"message": "Siaran dimulai", "status": audio_engine.get_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
def stop_audio():
    audio_engine.stop()
    return {"message": "Siaran dihentikan", "status": audio_engine.get_status()}

@app.get("/api/playback")
def get_playback_status():
    return audio_engine.get_status()

# --- SPEAKERS MONITORING & CRUD ---
class SpeakerCreate(BaseModel):
    name: str
    ip_address: str
    port: int = 5004
    zone: str = "Dermaga"

class SpeakerUpdate(BaseModel):
    name: str
    ip_address: str
    port: int = 5004
    zone: str = "Dermaga"
    enabled: int = 1

@app.get("/api/speakers")
def list_speakers():
    return get_all_speakers()

@app.post("/api/speakers")
def add_speaker(s: SpeakerCreate):
    try:
        new_id = create_speaker(s.name, s.ip_address, s.port, s.zone)
        log_event("SPEAKER_ADDED", f"Menambah speaker '{s.name}' ({s.ip_address}) ke {s.zone}")
        return {"message": "Speaker berhasil ditambahkan", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menambah speaker: {e}")

@app.put("/api/speakers/{speaker_id}")
def edit_speaker(speaker_id: int, s: SpeakerUpdate):
    existing = get_speaker_by_id(speaker_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    update_speaker(speaker_id, s.name, s.ip_address, s.port, s.zone, s.enabled)
    log_event("SPEAKER_UPDATED", f"Memperbarui speaker '{s.name}' ({s.ip_address})")
    return {"message": "Speaker berhasil diperbarui"}

@app.delete("/api/speakers/{speaker_id}")
def remove_speaker(speaker_id: int):
    existing = get_speaker_by_id(speaker_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    delete_speaker(speaker_id)
    log_event("SPEAKER_DELETED", f"Menghapus speaker '{existing['name']}' ({existing['ip_address']})")
    return {"message": "Speaker berhasil dihapus"}

@app.post("/api/speakers/{speaker_id}/ping")
async def ping_single_speaker(speaker_id: int):
    sp = get_speaker_by_id(speaker_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    is_online, latency = await ping_ip(sp["ip_address"])
    status = "online" if is_online else "offline"
    update_speaker_status(speaker_id, status, latency)
    updated = get_speaker_by_id(speaker_id)
    await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
    return {"online": is_online, "latency_ms": latency, "speaker": updated}

@app.post("/api/speakers/scan")
async def scan_all_speakers():
    updated_speakers = await scan_all_speakers_parallel()
    await manager.broadcast({"type": "speakers_update", "speakers": updated_speakers})
    return {"message": "Pemindaian selesai", "speakers": updated_speakers}

@app.post("/api/speakers/{speaker_id}/test-audio")
def test_speaker_audio_endpoint(speaker_id: int):
    sp = get_speaker_by_id(speaker_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    try:
        audio_engine.test_speaker_audio(sp["ip_address"], sp["port"])
        return {"message": f"Uji suara dikirim ke {sp['name']} ({sp['ip_address']})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ZONES MANAGEMENT ---
class ZoneCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class ZoneUpdate(BaseModel):
    name: str
    description: Optional[str] = ""

@app.get("/api/zones")
def list_zones():
    return get_all_zones()

@app.post("/api/zones")
async def add_zone(z: ZoneCreate):
    name = z.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nama zona tidak boleh kosong")
    try:
        new_id = create_zone(name, z.description or "")
        log_event("ZONE_CREATED", f"Menambah zona baru: '{name}'")
        await manager.broadcast({"type": "zones_update", "zones": get_all_zones()})
        return {"message": "Zona berhasil ditambahkan", "id": new_id, "name": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menambah zona: {e}")

@app.put("/api/zones/{zone_name}")
async def rename_zone(zone_name: str, z: ZoneUpdate):
    old_name = zone_name.strip()
    new_name = z.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Nama zona baru tidak boleh kosong")
    try:
        update_zone(old_name, new_name, z.description)
        log_event("ZONE_RENAMED", f"Mengubah nama zona '{old_name}' menjadi '{new_name}'")
        await manager.broadcast({"type": "zones_update", "zones": get_all_zones()})
        await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
        return {"message": "Zona berhasil diperbarui", "name": new_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memperbarui zona: {e}")

@app.delete("/api/zones/{zone_name}")
async def remove_zone(zone_name: str):
    name = zone_name.strip()
    try:
        delete_zone(name)
        log_event("ZONE_DELETED", f"Menghapus zona '{name}'")
        await manager.broadcast({"type": "zones_update", "zones": get_all_zones()})
        await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
        return {"message": f"Zona '{name}' berhasil dihapus"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menghapus zona: {e}")

# --- SCHEDULES ---
class ScheduleCreate(BaseModel):
    name: str
    audio_file_id: int
    schedule_type: str = "daily"
    time_str: str
    days_of_week: Optional[str] = "mon,tue,wed,thu,fri"
    interval_hours: Optional[int] = 2
    target_multicast: bool = True
    target_local: bool = True
    target_mode: Optional[str] = "all"
    target_zone: Optional[str] = ""
    target_speaker_id: Optional[int] = 0
    enabled: bool = True

@app.get("/api/schedules")
def list_schedules():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.*, a.display_name as audio_title 
            FROM schedules s
            LEFT JOIN audio_files a ON s.audio_file_id = a.id
            ORDER BY s.time_str ASC
        """).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/schedules")
def create_schedule(s: ScheduleCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO schedules (name, audio_file_id, schedule_type, time_str, days_of_week, interval_hours, target_multicast, target_local, target_mode, target_zone, target_speaker_id, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s.name, s.audio_file_id, s.schedule_type, s.time_str, s.days_of_week, s.interval_hours, int(s.target_multicast), int(s.target_local), s.target_mode or "all", s.target_zone or "", s.target_speaker_id or 0, int(s.enabled)))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_CREATED", f"Membuat jadwal baru: '{s.name}' pada {s.time_str}")
    return {"message": "Jadwal berhasil dibuat"}

@app.put("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: int, s: ScheduleCreate):
    with get_db() as conn:
        conn.execute("""
            UPDATE schedules 
            SET name = ?, audio_file_id = ?, schedule_type = ?, time_str = ?, 
                days_of_week = ?, interval_hours = ?, target_multicast = ?, target_local = ?,
                target_mode = ?, target_zone = ?, target_speaker_id = ?
            WHERE id = ?
        """, (s.name, s.audio_file_id, s.schedule_type, s.time_str, s.days_of_week, s.interval_hours, int(s.target_multicast), int(s.target_local), s.target_mode or "all", s.target_zone or "", s.target_speaker_id or 0, schedule_id))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_UPDATED", f"Memperbarui jadwal: '{s.name}' pada {s.time_str}")
    return {"message": "Jadwal berhasil diperbarui"}

@app.patch("/api/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT enabled, name FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

        new_val = 0 if row["enabled"] else 1
        conn.execute("UPDATE schedules SET enabled = ? WHERE id = ?", (new_val, schedule_id))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_TOGGLE", f"Mengubah status jadwal '{row['name']}' menjadi {'AKTIF' if new_val else 'NONAKTIF'}")
    return {"message": "Status jadwal diperbarui", "enabled": bool(new_val)}

@app.delete("/api/schedules/{schedule_id}")
def delete_schedule(schedule_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_DELETED", f"Menghapus jadwal id {schedule_id}")
    return {"message": "Jadwal berhasil dihapus"}

# --- HEALTH, SETTINGS & LOGS ---
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "IntanWave Audio Server"}

@app.get("/api/settings")
def read_settings():
    return get_settings()

@app.put("/api/settings")
def save_settings(payload: dict):
    update_settings(payload)
    return {"message": "Pengaturan disimpan", "settings": get_settings()}

@app.get("/api/logs")
def get_logs():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50").fetchall()
        return [dict(r) for r in rows]

# --- STATIC FRONTEND ASSETS ---
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
