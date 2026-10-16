# IntanWave PA System — Security Architecture & Threat Surface Map

## 1. System Overview & Tech Stack
- **Application**: IntanWave Network Public Address (PA) & Emergency Warning System (Pelindo Multi Terminal Tanjung Intan).
- **Backend Server (`backend/app/`)**:
  - **Runtime & Framework**: Python 3.11, FastAPI, Uvicorn, SQLite3 (`pa_system.db` in WAL mode), APScheduler, `pytz`.
  - **Media & Streaming Engine**: FFmpeg (`subprocess.Popen`) broadcasting RTP G.711u (`pcm_mulaw`, 8000 Hz) via UDP unicast (`tee` muxer) and UDP multicast (`239.x.x.x`), plus local ALSA (`plughw:0,0`) output.
  - **Deployment**: Docker container (`intanwave-audio-server`) running as `root` with `network_mode: host` and `privileged: true` on Debian server (`10.183.55.114` / Tailscale `100.98.69.62`), listening on `0.0.0.0:7080`.
- **Frontend (`frontend/`)**:
  - Static SPA (`index.html`, `app.js`, `styles.css`, `nodes.html`) served directly by FastAPI `StaticFiles` at `/`.
- **Windows Client Node (`client-windows/`)**:
  - **Runtime & Packaging**: Python 3.12 packaged into `IntanWave-Node.exe` via PyInstaller (`customtkinter`, `pystray`, `websocket-client`, `winotify`, bundled `ffplay.exe`).
  - **Function**: Connects to Backend via WebSocket (`/ws/node/{node_id}`), polls/pushes HTTP heartbeats (`POST /api/nodes/heartbeat`), syncs scheduled audio files (`GET /api/nodes/{node_id}/schedules` -> `GET /api/audio/stream-file/{filename}`), and plays local audio via `ffplay.exe` or fallback UDP RTP stream.

---

## 2. Trust Boundaries & Entry Points

```mermaid
flowchart LR
    subgraph LAN["Office & Harbor LAN (10.183.55.0/24 & 10.6.3.0/24) / Tailscale"]
        Browser["Operator Browser (Web UI)"]
        Attacker["Unauthenticated LAN Peer / Malicious Webpage"]
        WinNode["Windows Client Node (IntanWave-Node.exe)"]
        Horn["Outdoor IP Horn Speakers (10.6.3.x)"]
    end

    subgraph Server["Debian Server (10.183.55.114:7080) — Docker (root, privileged, host net)"]
        API["FastAPI REST & WS Endpoints"]
        DB[("SQLite3 (pa_system.db)")]
        FS[("Storage (/app/backend/storage/audio)")]
        FFmpeg["FFmpeg RTP Engine"]
    end

    Browser -->|HTTP REST / WS /ws| API
    Attacker -.->|Unauthenticated HTTP / CORS *| API
    WinNode <-->|WS /ws/node/{id} & HTTP Sync| API
    API --> DB
    API --> FS
    API --> FFmpeg
    FFmpeg -->|UDP RTP 5004| Horn
    FFmpeg -->|UDP RTP / WS Trigger| WinNode
```

### Unauthenticated HTTP & WebSocket Entry Points (`backend/app/main.py`)
| Endpoint | Method | Purpose | Auth Required |
|---|---|---|---|
| `/api/audio/upload` | `POST` | Upload `.mp3`/`.wav`/`.ogg`/`.aac`/`.m4a`/`.flac` to `AUDIO_DIR` | **None** |
| `/api/audio/{audio_id}` | `PUT` / `DELETE` | Rename/categorize or delete audio file from DB & disk | **None** |
| `/api/audio/stream-file/{filename}` | `GET` | Download raw audio file by filename (`Path(filename).name`) | **None** |
| `/api/play` | `POST` | Trigger immediate PA broadcast or emergency siren | **None** |
| `/api/stop` | `POST` | Stop active PA broadcast | **None** |
| `/api/schedules` | `POST` / `PUT` / `DELETE` | Create, modify, or delete automated broadcast schedules | **None** |
| `/api/speakers` | `POST` / `PUT` / `DELETE` | Create, modify, or delete IP speakers / client nodes | **None** |
| `/api/speakers/{id}/test-audio` | `POST` | Trigger test chime on a specific speaker | **None** |
| `/api/nodes/heartbeat` | `POST` | Auto-register or update IP/port/status of a Windows PC node | **None** |
| `/api/settings` | `POST` | Modify multicast IP/port, local audio toggle, horn buffer delay | **None** |
| `/ws` & `/ws/node/{node_id}` | `WS` | Real-time state broadcast & node command channel | **None** |

---

## 3. High-Risk Data Flows
1. **Multipart Filename & Metadata Flow (`upload_audio` -> `audio_files` -> Windows Client)**:
   - User-supplied `file.filename` in `POST /api/audio/upload` is joined directly with `AUDIO_DIR / file.filename` without `.name` sanitization, stored in SQLite, and later used by Windows clients (`self.media_dir / filename`) when downloading media.
   - User-supplied `name` (audio title) is broadcast over WebSocket in `play_audio` events (`title`) and passed by the Windows client into `winotify.Notification(title=..., msg=...)`, which interpolates `msg` into a PowerShell expandable here-string (`@" ... "@`).
2. **Broadcast Target Resolution (`POST /api/play`)**:
   - Resolves `target_mode` (`all`, `group`, `speaker`) against enabled speakers in SQLite. If the requested speaker/group yields an empty match, an `else: is_all_mode = True` branch silently escalates the broadcast to **all physical speakers**.
3. **FFmpeg Command Construction (`backend/app/audio_engine.py`)**:
   - Constructs `ffmpeg` CLI arguments using `ip_address` and `port` from the `speakers` table. When multiple unicast targets are active, builds a `tee` muxer string separated by `|` (`[select=a:f=rtp:...]rtp://{ep}?pkt_size=172`).
