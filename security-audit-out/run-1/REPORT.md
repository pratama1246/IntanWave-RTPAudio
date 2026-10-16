# IntanWave PA System — Executive Security Audit Report

- **Target Repository**: `d:\Project-Web\audio-server-ip-speaker` (`main` @ `32e1170`)
- **Audit Scope**: Backend FastAPI Server (`backend/app/`), Windows Client Node (`client-windows/`), Frontend Web Dashboard (`frontend/`), and Docker Deployment (`Dockerfile`, `docker-compose.yml`).
- **Methodology**: Deep white-box source review, data-flow taint tracing (source-to-sink), and false-positive elimination per `/security-audit`.

---

## 1. Executive Summary

| Severity | Count | Key Impact |
|---|---|---|
| **CRITICAL** | **2** | Remote Code Execution (RCE) on Windows Client PCs via Toast PowerShell Injection; Arbitrary File Overwrite via Path Traversal in Audio Upload & Client Sync |
| **HIGH** | **2** | Fail-open `/api/play` logic blasts all 12 physical outdoor harbor speakers when target ID is disabled/missing; Unauthenticated REST/WS APIs + wildcard CORS (`*`) allow unauthorized siren activation |
| **MEDIUM** | **1** | FFmpeg `tee` muxer slave option injection via unvalidated `ip_address` in speaker configuration |
| **Total** | **5** | All 5 findings are concretely exploitable with zero theoretical/noise findings included |

> [!NOTE]
> **SQL Injection Posture (Verified Safe)**: All database queries across `backend/app/main.py`, `backend/app/scheduler.py`, and `backend/app/database.py` consistently use parameterized SQLite placeholders (`?`). Dynamic `IN (?, ?)` clauses are constructed solely from integer-typed `List[int]` Pydantic fields or integer lengths (`",".join("?" * len(...))`). No SQL injection vulnerabilities exist.

---

## 2. Ranked Findings Summary

### 1. `[CRITICAL]` FINDING-001: Remote Code Execution on Windows Client Nodes via PowerShell Subexpression Injection in `winotify` Toast Notifications
- **Location**: `client-windows/receiver.py:424-451`, `client-windows/receiver.py:644`, `backend/app/main.py:186-214`
- **Root Cause**: When a broadcast starts on a Windows client node, `_play_local_file_task` calls `self.notify_toast("IntanWave — Siaran Audio", f"Memutar: {title}")`, where `title` is the audio's `name` from the server. `winotify` interpolates `title` and `msg` into a PowerShell expandable Here-String (`$Template = @" ... "@`) and executes `powershell.exe -Command`. Any `$(...)` PowerShell subexpression in an uploaded audio's `name` (e.g., `Pengumuman $(Start-Process calc.exe)`) executes arbitrary commands on every targeted Windows PC client.
- **Fix**: Strip or escape `$`, `` ` ``, `"`, `\r`, and `\n` in `notify_toast` (`client-windows/receiver.py:434`) before passing `title` and `msg` to `Notification(...)`.

### 2. `[CRITICAL]` FINDING-002: Arbitrary File Write via Path Traversal in Audio Upload (`POST /api/audio/upload`) and Client Media Sync
- **Location**: `backend/app/main.py:186-214`, `client-windows/receiver.py:519-521`, `client-windows/receiver.py:539-560`
- **Root Cause**: `upload_audio` checks `Path(file.filename).suffix.lower()` and writes directly to `save_path = AUDIO_DIR / file.filename` without `Path(file.filename).name` sanitization (unlike `/api/audio/stream-file/{filename}`, which properly uses `Path(filename).name`). An uploaded filename containing `../` or a leading `/` overwrites arbitrary files as `root` inside the privileged container, and propagates to Windows clients where `self.media_dir / filename` is similarly unsanitized.
- **Fix**: Enforce `safe_filename = Path(file.filename).name` in `backend/app/main.py:194` and `client-windows/receiver.py:543`.

### 3. `[HIGH]` FINDING-003: Dangerous Fail-Open Broadcast Logic in `/api/play` Blasts All Physical Harbor Speakers When Target Speaker/Group Is Missing or Disabled
- **Location**: `backend/app/main.py:346-389`
- **Root Cause**: In `play_audio`, if `target_mode` is `"speaker"` or `"group"` and the requested speaker/group ID is disabled (`enabled = 0`) or does not exist, `matching_dict` is empty and line 377 executes `else: is_all_mode = True`. Instead of returning `404 Not Found` (as `scheduler.py:94` does), the server broadcasts the audio to **all 12 physical outdoor IP speakers + multicast**.
- **Fix**: Replace `else: is_all_mode = True` when `req.target_mode != "all"` with `raise HTTPException(status_code=404, detail="Speaker atau grup target tidak ditemukan atau sedang nonaktif")`.

### 4. `[HIGH]` FINDING-004: Unauthenticated Administrative/Broadcast Endpoints & Wildcard CORS (`allow_origins=["*"]`)
- **Location**: `backend/app/main.py:30-36`, all `/api/*` and `/ws*` routes
- **Root Cause**: All API and WebSocket endpoints lack authentication and allow `Access-Control-Allow-Origin: *`. Any LAN host or any external website visited by an operator's browser (via cross-origin `fetch`) can trigger emergency sirens across the harbor, delete audio files, or spoof `POST /api/nodes/heartbeat` (`force_update=True`) to hijack a PC node's IP address.
- **Fix**: Restrict `allow_origins` to explicit dashboard origins (`http://10.183.55.114:7080`, `http://100.98.69.62:7080`) and introduce a lightweight API key/PIN for dashboard mutations and node heartbeats.

### 5. `[MEDIUM]` FINDING-005: FFmpeg `tee` Muxer Slave Option Injection via Unvalidated Speaker `ip_address`
- **Location**: `backend/app/main.py:656-684`, `backend/app/audio_engine.py:453-464`
- **Root Cause**: `SpeakerCreate` / `SpeakerUpdate` accepts arbitrary strings for `ip_address`. During multi-speaker RTP playback, `audio_engine.py:455` joins `rtp://{ep}?pkt_size=172` with `|` for FFmpeg's `-f tee` muxer. An `ip_address` containing `|[f=wav]/path/to/file.wav#` injects an additional `tee` slave output, writing arbitrary files on disk.
- **Fix**: Validate `ip_address` with `ipaddress.ip_address()` in `backend/app/models.py` or endpoint handlers.

---

## 3. Reference Files
- Architecture & Threat Model: `security-audit-out/run-1/architecture.md`
- Detailed PoCs & Code Fixes: `security-audit-out/run-1/FINDINGS-DETAIL.md`
- Machine-Readable JSON: `security-audit-out/run-1/findings.json`
