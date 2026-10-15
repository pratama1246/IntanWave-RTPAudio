import asyncio
import json
import os
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.config import AUDIO_DIR, BASE_DIR, DEFAULT_MULTICAST_IP, DEFAULT_MULTICAST_PORT
from app.database import (
    init_db, get_db, log_event, get_settings, update_settings,
    get_all_speakers, get_speaker_by_id, create_speaker, update_speaker, 
    delete_speaker, update_speaker_status,
    upsert_node_heartbeat, mark_stale_nodes_offline,
    get_all_groups, create_group, update_group, delete_group,
    get_all_zones, create_zone, update_zone, delete_zone,
    parse_groups
)
from app.audio_engine import audio_engine
from app.stream_hub import stream_hub
from app.scheduler import scheduler, reload_schedules, trigger_schedule_job
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
        # Kirim status awal seluruh speaker dan group
        try:
            speakers = get_all_speakers()
            await websocket.send_json({"type": "speakers_update", "speakers": speakers})
        except Exception:
            pass
        try:
            groups = get_all_groups()
            await websocket.send_json({"type": "groups_update", "groups": groups})
            await websocket.send_json({"type": "zones_update", "zones": groups})
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

def resolve_audio_file(filename: str, fallback_path: Optional[str] = None) -> Path:
    r"""
    Mengembalikan Path file audio yang valid secara portabel lintas OS & Docker container.
    Mencegah bug path absolut beda OS (misal D:\... dari Windows host yang terbawa ke Linux container).
    """
    fpath = AUDIO_DIR / filename
    if fpath.is_file():
        return fpath
    if fallback_path:
        fb = Path(fallback_path)
        if fb.is_file():
            return fb
        alt = AUDIO_DIR / fb.name
        if alt.is_file():
            return alt
    return fpath

def sync_audio_files_to_db():
    """Memindai folder audio dan mendaftarkan file yang belum tercatat atau sinkronisasi path."""
    valid_exts = {".wav", ".mp3", ".ogg", ".flac"}
    with get_db() as conn:
        for f in AUDIO_DIR.glob("*"):
            if f.suffix.lower() in valid_exts and f.is_file():
                existing = conn.execute("SELECT id FROM audio_files WHERE filename = ?", (f.name,)).fetchone()
                duration = audio_engine.get_audio_duration(str(f))
                if not existing:
                    name = f.stem.replace("_", " ").title()
                    lname = f.name.lower()
                    cat = "darurat" if any(k in lname for k in ["siren", "sirine", "ews", "emergency", "bahaya", "evakuasi"]) else "safety" if any(k in lname for k in ["safety", "k3", "briefing", "apd"]) else "biasa"
                    conn.execute("""
                        INSERT INTO audio_files (filename, display_name, file_path, format, duration, size, category)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (f.name, name, str(f.resolve()), f.suffix.lower()[1:], duration, f.stat().st_size, cat))
                else:
                    # Selalu sinkronkan file_path dan size agar sesuai dengan direktori aktif di OS/Container saat ini
                    conn.execute("""
                        UPDATE audio_files 
                        SET file_path = ?, size = ?, duration = CASE WHEN duration <= 0 THEN ? ELSE duration END
                        WHERE id = ?
                    """, (str(f.resolve()), f.stat().st_size, duration, existing["id"]))
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
    if cat in ("k3", "safety"):
        cat = "safety"
    elif cat not in ("biasa", "darurat", "safety"):
        cat = "biasa"

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO audio_files (filename, display_name, file_path, format, duration, size, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file.filename, disp_name, str(save_path.resolve()), ext[1:], duration, size, cat))
        conn.commit()

    log_event("AUDIO_UPLOADED", f"Berhasil mengunggah '{disp_name}' [{cat.upper()}] ({file.filename})")
    await manager.broadcast({"type": "audio_update", "audio_list": list_audio()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Upload berhasil", "filename": file.filename, "category": cat}

@app.patch("/api/audio/{audio_id}")
async def update_audio_info(audio_id: int, req: AudioUpdateRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")
        
        updates = []
        params = []
        cat = None
        if req.category is not None:
            cat = req.category.strip().lower()
            if cat in ("k3", "safety"):
                cat = "safety"
            if cat in ("biasa", "darurat", "safety"):
                updates.append("category = ?")
                params.append(cat)
        if req.display_name is not None and req.display_name.strip():
            updates.append("display_name = ?")
            params.append(req.display_name.strip())
            
        if updates:
            params.append(audio_id)
            conn.execute(f"UPDATE audio_files SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
            log_event("AUDIO_UPDATED", f"Memperbarui audio ID {audio_id}: [{cat.upper() if cat else row['category'].upper()}] {req.display_name or row['display_name']}")
            
    await manager.broadcast({"type": "audio_update", "audio_list": list_audio()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Audio berhasil diperbarui"}

@app.delete("/api/audio/{audio_id}")
async def delete_audio(audio_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")

        fpath = resolve_audio_file(row["filename"], row["file_path"])
        if fpath.exists():
            try:
                fpath.unlink()
            except Exception:
                pass

        conn.execute("DELETE FROM audio_files WHERE id = ?", (audio_id,))
        conn.commit()

    log_event("AUDIO_DELETED", f"Menghapus audio: '{row['display_name']}'")
    await manager.broadcast({"type": "audio_update", "audio_list": list_audio()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Audio berhasil dihapus"}

@app.get("/api/audio/{audio_id}/stream")
def stream_audio(audio_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM audio_files WHERE id = ?", (audio_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Audio tidak ditemukan")
        fpath = resolve_audio_file(row["filename"], row["file_path"])
        if not fpath.exists():
            raise HTTPException(status_code=404, detail="Berkas fisik tidak ditemukan")
        fmt = row["format"].lower()
        media_type = "audio/mpeg" if fmt == "mp3" else f"audio/{fmt}"
        return FileResponse(str(fpath), media_type=media_type)

@app.get("/api/audio/stream-file/{filename}")
def stream_audio_by_filename(filename: str):
    fpath = resolve_audio_file(filename)
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
    target_mode: Optional[str] = "all"  # 'all', 'group', 'zone', 'speaker', 'custom'
    target_group: Optional[str] = None
    target_groups: Optional[List[str]] = None
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

    # Pastikan file audio valid lintas platform (mengatasi path Windows absolut di Linux Docker)
    audio_path = resolve_audio_file(row["filename"], row["file_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"Berkas fisik audio '{row['filename']}' tidak ditemukan di storage server")

    target_endpoints = None
    target_desc = "Semua Speaker"

    # Hybrid Target Resolution: Mendukung kombinasi group DAN speaker spesifik sekaligus
    raw_groups = list(req.target_groups or [])
    if req.target_group:
        raw_groups.extend([g.strip() for g in req.target_group.replace("[","").replace("]","").replace('"','').split(",") if g.strip()])
    if req.target_zone:
        raw_groups.extend([g.strip() for g in req.target_zone.replace("[","").replace("]","").replace('"','').split(",") if g.strip()])
    target_groups = list(dict.fromkeys(raw_groups))

    raw_ids = list(req.speaker_ids or [])
    if req.speaker_id and req.speaker_id not in raw_ids:
        raw_ids.append(req.speaker_id)
    target_speaker_ids = list(dict.fromkeys(raw_ids))

    is_all_mode = (req.target_mode == "all" and not target_groups and not target_speaker_ids)

    if not is_all_mode and (target_groups or target_speaker_ids):
        matching_dict = {}
        with get_db() as conn:
            all_spk_rows = conn.execute("SELECT id, name, ip_address, port, groups, zone FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
            
            # 1. Match berdasarkan Group
            if target_groups:
                for r in all_spk_rows:
                    grps = parse_groups(r["groups"] or r["zone"])
                    if any(tg.lower() in [x.lower() for x in grps] or (r["zone"] and r["zone"].lower() == tg.lower()) for tg in target_groups):
                        matching_dict[r["id"]] = r

            # 2. Match berdasarkan Speaker ID spesifik
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
        # Mode "all" (Semua Speaker): Kirim ke seluruh IP speaker fisik terdaftar + Multicast
        with get_db() as conn:
            rows = conn.execute("SELECT ip_address, port FROM speakers WHERE enabled = 1 AND ip_address NOT LIKE 'pending-%'").fetchall()
            settings = get_settings()
            mc_ip = settings.get("multicast_ip", DEFAULT_MULTICAST_IP)
            mc_port = settings.get("multicast_port", str(DEFAULT_MULTICAST_PORT))
            target_endpoints = [f"{r['ip_address']}:{r['port']}" for r in rows]
            target_endpoints.append(f"{mc_ip}:{mc_port}")
            target_desc = f"Semua Speaker ({len(rows)} Speaker & Multicast)"

    try:
        cat = row["category"] if "category" in row.keys() else "biasa"
        audio_engine.play(
            file_path=str(audio_path.resolve()),
            title=row["display_name"],
            enable_multicast=req.enable_multicast,
            enable_local=req.enable_local,
            target_endpoints=target_endpoints,
            target_desc=target_desc,
            category=cat,
            is_manual=True
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

@app.get("/api/playback/sessions")
def get_playback_sessions():
    return audio_engine.get_status().get("active_sessions", [])

@app.post("/api/playback/sessions/{session_id}/stop")
def stop_playback_session(session_id: str):
    success = audio_engine.stop_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Sesi '{session_id}' tidak ditemukan")
    return {"message": f"Sesi {session_id} dihentikan", "status": audio_engine.get_status()}

@app.get("/api/playback/queue")
def get_playback_queue():
    return audio_engine.get_status().get("queue", [])

@app.delete("/api/playback/queue/{queue_id}")
def delete_playback_queue_item(queue_id: str):
    success = audio_engine.remove_queued_item(queue_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Item antrean '{queue_id}' tidak ditemukan")
    return {"message": f"Item antrean {queue_id} dihapus", "status": audio_engine.get_status()}

# --- SPEAKERS MONITORING & CRUD ---
class SpeakerCreate(BaseModel):
    name: str
    ip_address: str
    port: int = 5004
    groups: Optional[List[str]] = None
    group: Optional[str] = None
    zone: Optional[str] = None
    device_type: Optional[str] = "physical"

class SpeakerUpdate(BaseModel):
    name: str
    ip_address: str
    port: int = 5004
    groups: Optional[List[str]] = None
    group: Optional[str] = None
    zone: Optional[str] = None
    enabled: int = 1
    device_type: Optional[str] = "physical"

class NodeHeartbeatRequest(BaseModel):
    node_id: str
    device_name: Optional[str] = None
    groups: Optional[List[str]] = None
    group: Optional[str] = None
    zone: Optional[str] = None
    port: Optional[int] = 5004
    hostname: Optional[str] = None
    client_ip: Optional[str] = None
    force_update: Optional[bool] = False

@app.post("/api/nodes/heartbeat")
async def node_heartbeat(req: NodeHeartbeatRequest, request: Request):
    """
    Endpoint deteksi otomatis (auto-discovery) dan heartbeat dinamis untuk PC client Windows (DHCP).
    Merekam IP aktif pengirim secara otomatis dan menyinkronkan dengan database server.
    """
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    elif request.headers.get("X-Real-IP"):
        client_ip = request.headers.get("X-Real-IP").strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = ""

    if (client_ip in ("127.0.0.1", "localhost", "::1", "") and req.client_ip):
        client_ip = req.client_ip
    elif not client_ip:
        client_ip = req.client_ip or "127.0.0.1"

    node = upsert_node_heartbeat(
        node_id=req.node_id,
        device_name=req.device_name or "",
        groups=req.groups or req.group or req.zone,
        zone=req.zone or "",
        ip_address=client_ip,
        port=req.port or 5004,
        hostname=req.hostname or "",
        force_update=bool(req.force_update)
    )

    # Broadcast pembaruan speaker & group seketika ke Web Dashboard
    await manager.broadcast({
        "type": "speakers_update",
        "speakers": get_all_speakers()
    })
    await manager.broadcast({
        "type": "groups_update",
        "groups": get_all_groups()
    })
    await manager.broadcast({
        "type": "zones_update",
        "zones": get_all_groups()
    })

    return {
        "status": "ok",
        "node": node
    }

@app.get("/api/stream")
async def stream_live(request: Request, node_id: str = ""):
    """
    Stream audio live (PCM 16-bit 44.1kHz mono, mentah) untuk PC client Windows.
    Koneksi dibiarkan terbuka; data hanya mengalir saat ada siaran yang menarget node ini.
    """
    node_id = (node_id or "").strip()
    if not node_id:
        raise HTTPException(status_code=400, detail="node_id wajib diisi")

    token, q = stream_hub.subscribe(node_id, asyncio.get_running_loop())

    async def gen():
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    continue
                if chunk == b"STREAM_END":
                    continue
                chunks = [chunk]
                while not q.empty() and len(chunks) < 10:
                    try:
                        c = q.get_nowait()
                        if c != b"STREAM_END":
                            chunks.append(c)
                    except asyncio.QueueEmpty:
                        break
                if chunks:
                    yield b"".join(chunks)
        finally:
            stream_hub.unsubscribe(token)

    return StreamingResponse(
        gen(),
        media_type="audio/mpeg",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no", "X-Audio-Format": "mp3;rate=44100;ch=1;bitrate=128k"},
    )

@app.websocket("/ws/node/{node_id}")
async def ws_node_stream(websocket: WebSocket, node_id: str):
    """
    Koneksi WebSocket real-time untuk PC client Windows (IntanWave Node).
    Mendukung transmisi audio instan (binary frames) dan heartbeat/ping-pong otomatis.
    """
    node_id = (node_id or "").strip()
    if not node_id:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    token, q = stream_hub.subscribe(node_id, asyncio.get_running_loop())
    
    # Perbarui status speaker jadi online
    now_iso = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("UPDATE speakers SET status = 'online', latency_ms = 1, last_online = ? WHERE node_id = ?", (now_iso, node_id))
        conn.commit()

    async def send_audio():
        while True:
            chunk = await q.get()
            if chunk == b"STREAM_END":
                await websocket.send_text(json.dumps({"type": "stream_end"}))
                continue
            if chunk.startswith(b"JSON:"):
                try:
                    await websocket.send_text(chunk[5:].decode("utf-8"))
                except Exception:
                    pass
                continue
            chunks = [chunk]
            has_end = False
            json_to_send = None
            while not q.empty() and len(chunks) < 10:
                try:
                    c = q.get_nowait()
                    if c == b"STREAM_END":
                        has_end = True
                        break
                    if c.startswith(b"JSON:"):
                        json_to_send = c[5:].decode("utf-8")
                        break
                    chunks.append(c)
                except asyncio.QueueEmpty:
                    break
            if chunks:
                await websocket.send_bytes(b"".join(chunks))
            if json_to_send:
                try:
                    await websocket.send_text(json_to_send)
                except Exception:
                    pass
            if has_end:
                await websocket.send_text(json.dumps({"type": "stream_end"}))

    async def recv_heartbeat():
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
            elif msg.startswith("{"):
                try:
                    data = json.loads(msg)
                    if data.get("type") == "heartbeat":
                        upsert_node_heartbeat(
                            node_id=node_id,
                            device_name=data.get("device_name"),
                            ip_address=websocket.client.host if websocket.client else "127.0.0.1",
                            port=data.get("port", 5004),
                            groups=data.get("groups"),
                            hostname=data.get("hostname", "")
                        )
                except Exception:
                    pass

    try:
        await asyncio.gather(send_audio(), recv_heartbeat())
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        stream_hub.unsubscribe(token)

@app.get("/api/speakers")
def list_speakers():
    return get_all_speakers()

@app.post("/api/speakers")
async def add_speaker(s: SpeakerCreate):
    try:
        grps = parse_groups(s.groups if s.groups is not None else (s.group or s.zone or "Kantor"))
        if not grps:
            grps = ["Kantor"]
        new_id = create_speaker(s.name, s.ip_address, s.port, groups=grps, zone=grps[0], device_type=s.device_type or "physical")
        log_event("SPEAKER_ADDED", f"Menambah speaker '{s.name}' ({s.ip_address}) ke group: {', '.join(grps)}")
        await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
        await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
        await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
        return {"message": "Speaker berhasil ditambahkan", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menambah speaker: {e}")

@app.put("/api/speakers/{speaker_id}")
async def edit_speaker(speaker_id: int, s: SpeakerUpdate):
    existing = get_speaker_by_id(speaker_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    grps = parse_groups(s.groups if s.groups is not None else (s.group or s.zone or "Kantor"))
    if not grps:
        grps = ["Kantor"]
    update_speaker(speaker_id, s.name, s.ip_address, s.port, groups=grps, zone=grps[0], enabled=s.enabled)
    log_event("SPEAKER_UPDATED", f"Memperbarui speaker '{s.name}' ({s.ip_address})")
    await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
    await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
    await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
    return {"message": "Speaker berhasil diperbarui"}

@app.delete("/api/speakers/{speaker_id}")
async def remove_speaker(speaker_id: int):
    existing = get_speaker_by_id(speaker_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")
    delete_speaker(speaker_id)
    log_event("SPEAKER_DELETED", f"Menghapus speaker '{existing['name']}' ({existing['ip_address']})")
    await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
    await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
    await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
    return {"message": "Speaker berhasil dihapus"}

@app.post("/api/speakers/{speaker_id}/ping")
async def ping_single_speaker(speaker_id: int):
    sp = get_speaker_by_id(speaker_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Speaker tidak ditemukan")

    if sp.get("device_type") == "node":
        last_online_str = sp.get("last_online")
        is_online = False
        if last_online_str:
            try:
                from datetime import datetime
                is_online = (datetime.now() - datetime.fromisoformat(last_online_str)).total_seconds() <= 45
            except Exception:
                pass
        status = "online" if is_online else "offline"
        latency = 1 if is_online else 0
    else:
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
        audio_engine.test_speaker_audio(sp["ip_address"], sp["port"], node_id=sp.get("node_id"))
        return {"message": f"Uji suara dikirim ke {sp['name']} ({sp['ip_address']})"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- GROUPS & ZONES MANAGEMENT ---
class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class GroupUpdate(BaseModel):
    name: str
    description: Optional[str] = ""

@app.get("/api/groups")
def list_groups():
    return get_all_groups()

@app.post("/api/groups")
async def add_group(g: GroupCreate):
    name = g.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nama group tidak boleh kosong")
    try:
        new_id = create_group(name, g.description or "")
        log_event("GROUP_CREATED", f"Menambah group baru: '{name}'")
        await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
        await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
        return {"message": "Group berhasil ditambahkan", "id": new_id, "name": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menambah group: {e}")

@app.put("/api/groups/{group_name}")
async def rename_group(group_name: str, g: GroupUpdate):
    old_name = group_name.strip()
    new_name = g.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Nama group baru tidak boleh kosong")
    try:
        update_group(old_name, new_name, g.description)
        log_event("GROUP_RENAMED", f"Mengubah nama group '{old_name}' menjadi '{new_name}'")
        await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
        await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
        await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
        return {"message": "Group berhasil diperbarui", "name": new_name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal memperbarui group: {e}")

@app.delete("/api/groups/{group_name}")
async def remove_group(group_name: str):
    name = group_name.strip()
    try:
        delete_group(name)
        log_event("GROUP_DELETED", f"Menghapus group '{name}'")
        await manager.broadcast({"type": "groups_update", "groups": get_all_groups()})
        await manager.broadcast({"type": "zones_update", "zones": get_all_groups()})
        await manager.broadcast({"type": "speakers_update", "speakers": get_all_speakers()})
        return {"message": f"Group '{name}' berhasil dihapus"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal menghapus group: {e}")

# Legacy Zone Endpoints (Alias ke Groups)
class ZoneCreate(GroupCreate):
    pass

class ZoneUpdate(GroupUpdate):
    pass

@app.get("/api/zones")
def list_zones():
    return get_all_groups()

@app.post("/api/zones")
async def add_zone(z: ZoneCreate):
    return await add_group(z)

@app.put("/api/zones/{zone_name}")
async def rename_zone(zone_name: str, z: ZoneUpdate):
    return await rename_group(zone_name, z)

@app.delete("/api/zones/{zone_name}")
async def remove_zone(zone_name: str):
    return await remove_group(zone_name)

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
    target_group: Optional[str] = ""
    target_zone: Optional[str] = ""
    target_speaker_id: Optional[int] = 0
    target_speakers: Optional[str] = ""
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

@app.get("/api/nodes/{node_id}/schedules")
def list_node_schedules(node_id: str):
    """
    Mengambil daftar jadwal siaran yang HANYA relevan / menargetkan node PC ini.
    Termasuk target 'all', target grup yang cocok, atau target speaker ID yang cocok.
    Jadwal yang hanya untuk speaker fisik lain (misal Dermaga) otomatis diabaikan.
    """
    node_id = (node_id or "").strip()
    with get_db() as conn:
        node_spk = conn.execute(
            "SELECT * FROM speakers WHERE node_id = ? AND enabled = 1", (node_id,)
        ).fetchone()
        if not node_spk:
            return []

        node_id_int = node_spk["id"]
        node_groups = [g.lower() for g in parse_groups(node_spk["groups"] or node_spk["zone"])]

        rows = conn.execute("""
            SELECT s.*, a.display_name as audio_title, a.filename as audio_filename, a.duration as audio_duration, a.size as audio_size
            FROM schedules s
            LEFT JOIN audio_files a ON s.audio_file_id = a.id
            WHERE s.enabled = 1
            ORDER BY s.time_str ASC
        """).fetchall()

        matched = []
        for r in rows:
            tmode = r["target_mode"] or "all"
            tgroup_raw = r["target_group"] or r["target_zone"] or ""
            target_groups = [g.lower() for g in parse_groups(tgroup_raw)]

            target_speaker_ids = []
            if r["target_speaker_id"]:
                target_speaker_ids.append(r["target_speaker_id"])
            if r["target_speakers"]:
                for x in str(r["target_speakers"]).split(","):
                    if x.strip().isdigit():
                        target_speaker_ids.append(int(x.strip()))

            is_all = (tmode == "all" and not target_groups and not target_speaker_ids)
            group_match = any(g in node_groups for g in target_groups)
            speaker_match = (node_id_int in target_speaker_ids)

            if is_all or group_match or speaker_match:
                item = dict(r)
                matched.append(item)

        return matched

def normalize_time_str(time_str: str) -> str:
    """Membersihkan, mendeduplikasi, dan mengurutkan secara kronologis multi-jam (misal '15:00, 08:00' -> '08:00, 15:00')."""
    if not time_str:
        return "08:00"
    times = set()
    for t in time_str.split(","):
        t_clean = t.strip()
        if ":" in t_clean:
            parts = t_clean.split(":")
            try:
                h = int(parts[0])
                m = int(parts[1])
                if 0 <= h <= 23 and 0 <= m <= 59:
                    times.add(f"{h:02d}:{m:02d}")
            except Exception:
                pass
    if not times:
        return "08:00"
    return ", ".join(sorted(list(times)))

@app.post("/api/schedules")
async def create_schedule(s: ScheduleCreate):
    t_group = (s.target_group or s.target_zone or "").strip()
    norm_time = normalize_time_str(s.time_str)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO schedules (name, audio_file_id, schedule_type, time_str, days_of_week, interval_hours, target_multicast, target_local, target_mode, target_group, target_zone, target_speaker_id, target_speakers, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s.name, s.audio_file_id, s.schedule_type, norm_time, s.days_of_week, s.interval_hours, int(s.target_multicast), int(s.target_local), s.target_mode or "all", t_group, t_group, s.target_speaker_id or 0, s.target_speakers or "", int(s.enabled)))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_CREATED", f"Membuat jadwal baru: '{s.name}' pada {norm_time}")
    await manager.broadcast({"type": "schedules_update", "schedules": list_schedules()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Jadwal berhasil dibuat"}

@app.put("/api/schedules/{schedule_id}")
async def update_schedule(schedule_id: int, s: ScheduleCreate):
    t_group = (s.target_group or s.target_zone or "").strip()
    norm_time = normalize_time_str(s.time_str)
    with get_db() as conn:
        conn.execute("""
            UPDATE schedules 
            SET name = ?, audio_file_id = ?, schedule_type = ?, time_str = ?, 
                days_of_week = ?, interval_hours = ?, target_multicast = ?, target_local = ?,
                target_mode = ?, target_group = ?, target_zone = ?, target_speaker_id = ?, target_speakers = ?
            WHERE id = ?
        """, (s.name, s.audio_file_id, s.schedule_type, norm_time, s.days_of_week, s.interval_hours, int(s.target_multicast), int(s.target_local), s.target_mode or "all", t_group, t_group, s.target_speaker_id or 0, s.target_speakers or "", schedule_id))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_UPDATED", f"Memperbarui jadwal: '{s.name}' pada {norm_time}")
    await manager.broadcast({"type": "schedules_update", "schedules": list_schedules()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Jadwal berhasil diperbarui"}

@app.patch("/api/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT enabled, name FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

        new_val = 0 if row["enabled"] else 1
        conn.execute("UPDATE schedules SET enabled = ? WHERE id = ?", (new_val, schedule_id))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_TOGGLE", f"Mengubah status jadwal '{row['name']}' menjadi {'AKTIF' if new_val else 'NONAKTIF'}")
    await manager.broadcast({"type": "schedules_update", "schedules": list_schedules()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Status jadwal diperbarui", "enabled": bool(new_val)}

@app.delete("/api/schedules/{schedule_id}")
async def delete_schedule(schedule_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        conn.commit()

    reload_schedules()
    log_event("SCHEDULE_DELETED", f"Menghapus jadwal id {schedule_id}")
    await manager.broadcast({"type": "schedules_update", "schedules": list_schedules()})
    stream_hub.publish_event({"type": "schedules_update"}, all_nodes=True)
    return {"message": "Jadwal berhasil dihapus"}

_last_manual_triggers = {}

@app.post("/api/schedules/{schedule_id}/trigger")
def trigger_schedule_manually(schedule_id: int):
    """Memicu jadwal berbunyi seketika sesuai target spesifik yang tersimpan di jadwal tersebut."""
    now = time.time()
    if _last_manual_triggers.get(schedule_id) and (now - _last_manual_triggers[schedule_id] < 1.5):
        return {"message": "Permintaan beruntun diabaikan (anti dobel-klik)", "status": "debounced"}
    _last_manual_triggers[schedule_id] = now

    with get_db() as conn:
        row = conn.execute("SELECT id, name FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Jadwal tidak ditemukan")

    threading.Thread(target=trigger_schedule_job, args=[schedule_id, True], daemon=True).start()
    log_event("SCHEDULE_MANUAL_TRIGGER", f"Memicu siaran jadwal secara manual: '{row['name']}'")
    return {"message": f"Jadwal '{row['name']}' sedang disiarkan sesuai targetnya"}

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

@app.get("/api/time")
def get_server_time():
    now = datetime.now()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.timestamp(),
        "timezone": "WIB"
    }

@app.get("/api/logs")
def get_logs():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, 
                   COALESCE(datetime(timestamp, 'localtime'), timestamp) AS timestamp, 
                   level, event, details 
            FROM logs 
            ORDER BY id DESC LIMIT 100
        """).fetchall()
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
