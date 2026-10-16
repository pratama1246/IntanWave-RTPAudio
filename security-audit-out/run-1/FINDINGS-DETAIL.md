# IntanWave PA System — Detailed Security Findings

## FINDING-001: Remote Code Execution on Windows Client Nodes via PowerShell Subexpression Injection in `winotify` Toast Notifications
- **Severity**: CRITICAL (CVSS 9.8)
- **Confidence**: HIGH
- **Component**: `client-windows/receiver.py:424-451`, `client-windows/receiver.py:644`, `backend/app/main.py:186-214`, `backend/app/main.py:424`
- **Vulnerability Class**: OS Command Injection / PowerShell Expandable Here-String Injection (CWE-78)

### Technical Description
When a Windows Client Node (`IntanWave-Node.exe`) receives a `play_audio` event over WebSocket (`/ws/node/{node_id}`), `_handle_play_event` (`client-windows/receiver.py:574`) extracts `title = data.get("title") or filename or "Siaran Audio"`, which originates from the user-supplied `name` field of an uploaded audio file (`POST /api/audio/upload`).

In `_play_local_file_task` (`client-windows/receiver.py:644`), the client displays a Windows Toast notification:
```python
self.notify_toast("IntanWave — Siaran Audio", f"Memutar: {title}")
```
`notify_toast` (`client-windows/receiver.py:445-447`) instantiates `winotify.Notification(app_id="IntanWave Audio System", title=title, msg=msg, duration="short")` and calls `toast.show()`. Under the hood, `winotify` formats `winotify.TEMPLATE` using `TEMPLATE.format(**self.__dict__)` and passes the resulting string directly to `powershell.exe -Command`:
```powershell
$Template = @"
<toast {launch} duration="{duration}">
    <visual>
        <binding template="ToastImageAndText02">
            <image id="1" src="{icon}" />
            <text id="1"><![CDATA[{title}]]></text>
            <text id="2"><![CDATA[{msg}]]></text>
        </binding>
    </visual>
...
"@
```
Because `winotify` uses a double-quoted PowerShell Here-String (`@" ... "@`), PowerShell evaluates any `$(...)` subexpression or `$variable` inside `{title}` and `{msg}` before constructing the XML string.

### Proof of Concept (Exploit Chain)
1. An attacker on the LAN (or via CSRF from a browser) uploads a valid `.wav` file with a malicious `name` parameter:
   ```bash
   curl -X POST http://10.183.55.114:7080/api/audio/upload \
     -F "name=Pengumuman \$(Start-Process calc.exe)" \
     -F "category=biasa" \
     -F "file=@test_chime.wav"
   ```
2. The attacker triggers playback of the uploaded `audio_id` targeting a Windows client node (or all nodes):
   ```bash
   curl -X POST http://10.183.55.114:7080/api/play \
     -H "Content-Type: application/json" \
     -d '{"audio_id": 15, "target_mode": "speaker", "speaker_id": 14, "speaker_ids": [14], "enable_multicast": false, "enable_local": false}'
   ```
3. Every targeted Windows PC running `IntanWave-Node.exe` receives the WebSocket broadcast, calls `notify_toast`, and executes `Start-Process calc.exe` under the logged-in Windows user's security context.

### Remediation
Sanitize `title` and `msg` in `client-windows/receiver.py:434` before passing them to `winotify.Notification` by escaping PowerShell special characters (specifically backticks `` ` ``, dollar signs `$`, double quotes `"`, and newlines) or stripping `$` and `"` altogether:
```python
safe_title = str(title).replace("`", "").replace("$", "").replace('"', "'").replace("\r", " ").replace("\n", " ")
safe_msg = str(msg).replace("`", "").replace("$", "").replace('"', "'").replace("\r", " ").replace("\n", " ")
```

---

## FINDING-002: Arbitrary File Write via Path Traversal in Audio Upload (`POST /api/audio/upload`) and Client Media Sync
- **Severity**: CRITICAL (CVSS 9.1)
- **Confidence**: HIGH
- **Component**: `backend/app/main.py:186-214`, `client-windows/receiver.py:519-521`, `client-windows/receiver.py:539-560`, `client-windows/receiver.py:605-615`
- **Vulnerability Class**: Path Traversal / Arbitrary File Overwrite (CWE-22)

### Technical Description
In `backend/app/main.py:186-205` (`upload_audio`), the server validates the file extension of `file.filename` and constructs `save_path` without stripping directory components:
```python
ext = Path(file.filename).suffix.lower()
if ext not in allowed_extensions:
    raise HTTPException(status_code=400, detail=f"Format tidak didukung...")

save_path = AUDIO_DIR / file.filename
with open(save_path, "wb") as buffer:
    shutil.copyfileobj(file.file, buffer)
```
In Python's `pathlib.Path`:
1. If `file.filename` contains `../` traversal sequences (e.g., `../../app/test.wav`), `AUDIO_DIR / file.filename` resolves outside `AUDIO_DIR`.
2. If `file.filename` is an absolute path starting with `/` (e.g., `/etc/cron.d/backdoor.wav`), `AUDIO_DIR / "/etc/cron.d/backdoor.wav"` completely discards `AUDIO_DIR` and resolves to `/etc/cron.d/backdoor.wav`! Because the Docker container runs as `root` with `privileged: true`, any path writable by `root` can be overwritten with a file ending in an audio extension.
3. Furthermore, `file.filename` is saved verbatim into the `audio_files` SQLite table (`backend/app/main.py:210`) and sent to Windows client nodes during schedule sync (`client-windows/receiver.py:519`) and WebSocket playback (`client-windows/receiver.py:605`), where `target_path = self.media_dir / filename` also performs unsanitized `Path` joining.

### Proof of Concept
```bash
curl -X POST http://10.183.55.114:7080/api/audio/upload \
  -F "name=TraversalTest" \
  -F "category=biasa" \
  -F 'file=@test_chime.wav;filename="../../traversal_poc.wav"'
```
This writes `traversal_poc.wav` outside `/app/backend/storage/audio` into `/app/backend/traversal_poc.wav`.

### Remediation
1. **Backend (`backend/app/main.py:194`)**: Sanitize `file.filename` using `Path(file.filename).name` and reject empty or hidden filenames before constructing `save_path`:
   ```python
   safe_filename = Path(file.filename or "").name
   if not safe_filename or safe_filename.startswith("."):
       raise HTTPException(status_code=400, detail="Nama file tidak valid")
   save_path = (AUDIO_DIR / safe_filename).resolve()
   if save_path.parent != AUDIO_DIR.resolve():
       raise HTTPException(status_code=400, detail="Path file tidak valid")
   ```
2. **Windows Client (`client-windows/receiver.py:543`, `519`, `605`)**: Always sanitize `filename = Path(filename).name` before joining with `self.media_dir`.

---

## FINDING-003: Dangerous Fail-Open Broadcast Logic in `/api/play` Blasts All Physical Harbor Speakers When Target Speaker/Group Is Missing or Disabled
- **Severity**: HIGH (CVSS 7.5 — Operational & Physical Safety Impact)
- **Confidence**: HIGH
- **Component**: `backend/app/main.py:346-389`
- **Vulnerability Class**: Improper Fallback / Business Logic Flaw (CWE-636 / CWE-840)

### Technical Description
In `backend/app/main.py:346-389` (`play_audio`), when a client requests targeted playback (`target_mode="speaker"` or `target_mode="group"`), the endpoint queries `SELECT * FROM speakers WHERE enabled = 1` and filters `matching_dict` by the requested speaker IDs or group IDs.

However, lines 369–378 contain a dangerous `else` fallback:
```python
    if matching_dict:
        matching_speakers = list(matching_dict.values())
        for s in matching_speakers:
            if s["device_type"] == "client_node" and s.get("node_id"):
                ws_node_ids.add(s["node_id"])
            else:
                rtp_endpoints.append(f"{s['ip_address']}:{s['port']}")
    else:
        is_all_mode = True
        target_desc = "Semua Area / Speaker"
```
If the targeted speaker was recently disabled (`enabled = 0`), deleted, or a stale/invalid `speaker_id` is passed in the API request, `matching_dict` is empty (`{}`). Instead of aborting with `HTTPException(status_code=404, detail="Speaker target tidak ditemukan atau sedang nonaktif")` (as `scheduler.py:94-96` correctly does for scheduled broadcasts), `/api/play` sets `is_all_mode = True` and proceeds to broadcast the audio across **all 12 physical outdoor IP horn speakers (`10.6.3.x`), all client nodes, and UDP multicast**!

### Impact
A single typo in `speaker_id`, a race condition where an admin disables a speaker right before clicking "Play", or an isolated test call referencing a stale speaker ID will unexpectedly blast audio or emergency sirens across the entire Pelindo Tanjung Intan port facility.

### Remediation
Replace the `else: is_all_mode = True` fallback in `backend/app/main.py:376-378` when `req.target_mode != "all"`:
```python
    if req.target_mode != "all":
        if not matching_dict:
            conn.close()
            raise HTTPException(
                status_code=404,
                detail="Speaker atau grup target tidak ditemukan atau sedang dinonaktifkan."
            )
```

---

## FINDING-004: Complete Absence of Authentication & Permissive CORS (`allow_origins=["*"]`) Across Administrative, Broadcast, and Node Control APIs
- **Severity**: HIGH (CVSS 8.6)
- **Confidence**: HIGH
- **Component**: `backend/app/main.py:30-36`, all `/api/*` and `/ws*` routes
- **Vulnerability Class**: Missing Authentication for Critical Function (CWE-306) & Cross-Origin Resource Sharing Misconfiguration (CWE-942)

### Technical Description
1. **No Authentication on Critical PA Controls**: Every REST endpoint (`/api/play`, `/api/stop`, `/api/audio/upload`, `DELETE /api/audio/{id}`, `POST/PUT/DELETE /api/speakers`, `POST /api/nodes/heartbeat`, `POST /api/settings`) and WebSocket endpoint (`/ws`, `/ws/node/{node_id}`) is accessible without authentication to any host able to reach port `7080` on the LAN (`10.183.55.0/24`) or Tailscale VPN.
2. **Drive-By Cross-Origin Exploitation (`allow_origins=["*"]`)**: Because `CORSMiddleware` is configured with `allow_origins=["*"]` and `allow_methods=["*"]` (`backend/app/main.py:30-36`), any external website visited by an operator on the office LAN can issue `fetch("http://10.183.55.114:7080/api/play", ...)` requests from JavaScript in the operator's browser to trigger port-wide emergency sirens (`sirine_ews_test.wav`), delete all audio files, or reconfigure speaker IPs.
3. **Node Hijacking via Unauthenticated Heartbeat/WebSocket**: Any peer can call `POST /api/nodes/heartbeat` with `"node_id": "node_tamaodyssey", "force_update": true, "ip_address": "<attacker_ip>"` to overwrite the registered IP address of a legitimate PC node or impersonate it on `/ws/node/node_tamaodyssey`.

### Remediation
1. **Short-Term (Zero-Friction Hardening)**:
   - Restrict `CORSMiddleware` `allow_origins` to the server's explicit origins (`http://10.183.55.114:7080`, `http://100.98.69.62:7080`, `http://localhost:7080`) instead of `["*"]`.
   - Add a shared node API token (`X-Node-Token`) for `/api/nodes/*` and `/ws/node/*`, and HTTP Basic Auth or session PIN for the Web Dashboard.

---

## FINDING-005: FFmpeg `tee` Muxer Slave Option & Arbitrary File Write Injection via Unvalidated Speaker `ip_address`
- **Severity**: MEDIUM (CVSS 6.5)
- **Confidence**: HIGH
- **Component**: `backend/app/main.py:656-684`, `backend/app/audio_engine.py:453-464`
- **Vulnerability Class**: Argument / Muxer Option Injection (CWE-88)

### Technical Description
When creating (`POST /api/speakers`) or updating (`PUT /api/speakers/{id}`) a speaker, `SpeakerCreate` (`backend/app/models.py:36-44`) defines `ip_address: str` without validating that it is a valid IPv4/IPv6 address.

When `AudioEngine.play` (`backend/app/audio_engine.py:453-460`) streams to 2 or more RTP endpoints, it constructs an FFmpeg `tee` muxer string by interpolating each `ep` (`{ip_address}:{port}`) and joining them with `|`:
```python
tee_targets = "|".join(
    [f"[select=a:f=rtp:ssrc={shared_ssrc}:seq=0]rtp://{ep}?pkt_size=172" for ep in unique_eps]
)
cmd.extend([
    "-map", "0:a",
    "-c:a", "pcm_mulaw",
    "-ar", "8000",
    "-ac", "1",
    "-f", "tee",
    tee_targets
])
```
In FFmpeg's `tee` muxer, `|` separates slave outputs and `[f=...]` specifies the output format and options for each slave. If a speaker record is created or updated with `ip_address = "127.0.0.1:5004|[f=wav]/app/backend/storage/overwritten.wav#"`, the injected `|[f=wav]/path` is parsed by FFmpeg's `tee` muxer as an additional local file output, allowing arbitrary file overwrite inside the container whenever multi-speaker RTP broadcast runs.

### Remediation
Validate `ip_address` in `SpeakerCreate`, `SpeakerUpdate`, `NodeHeartbeatRequest`, and `SettingsUpdate` using Python's standard library `ipaddress.ip_address()`:
```python
import ipaddress
try:
    ipaddress.ip_address(speaker.ip_address.strip())
except ValueError:
    raise HTTPException(status_code=400, detail="Format IP Address tidak valid")
```
