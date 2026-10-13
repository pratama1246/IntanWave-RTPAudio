# PRD — IP Audio PA System

**Version:** 0.2.0  
**Status:** Draft / Prototype

## 1. Overview

IP Audio PA System is a centralized network audio system built around the existing **dedicated Windows PC currently used for office alarms**.

The Windows PC currently uses Free Alarm Clock and sends audio to an amplifier and internal office speakers. The new system will eventually make this PC the central PA server while also acting as a local audio endpoint.

The same server will broadcast audio to IP speakers through **RTP multicast**.

```text
                    Windows PA Server
                 ┌─────────────────────┐
                 │ Audio Library       │
                 │ Scheduler           │
                 │ FastAPI             │
                 │ Dashboard           │
                 │ FFmpeg / RTP        │
                 └─────────┬───────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
        RTP Multicast              Windows Audio
              │                         │
              ▼                         ▼
        Network / Switch             Amplifier
              │                         │
       ┌──────┼──────┐                  ▼
       ▼      ▼      ▼             Internal Speakers
     IP SPK  IP SPK  IP SPK
```

## 2. Problem

Current IP speakers can store audio files individually. The internal office PA uses a separate Windows PC + Free Alarm Clock + amplifier.

The target system centralizes:

- Audio storage.
- Scheduling.
- Manual playback.
- IP-speaker streaming.
- Internal amplifier playback.

The IP speakers should receive audio over the network instead of requiring permanent copies of broadcast files.

## 3. Goals

### Primary

1. Use the existing Windows alarm PC as the initial PA server.
2. Stream audio to IP speakers using RTP multicast.
3. Play audio through the Windows PC's existing amplifier output.
4. Store audio centrally.
5. Provide Play/Stop controls.
6. Provide recurring and one-time schedules.
7. Support common formats through FFmpeg.
8. Provide a simple web dashboard.
9. Keep resource usage low enough for the existing PC.

### Secondary

- Playback status and logs.
- Audio upload/management.
- FFmpeg recovery.
- Future emergency/priority announcements.
- Future SIP/IP Phone integration.

## 4. Non-Goals for v0.1

- Replacing or modifying the existing SIP/IP Phone system.
- Building a SIP PBX.
- Per-speaker targeting.
- Multiple independent zones.
- Mobile application.
- Cloud hosting.
- Speaker firmware modification.
- Permanent broadcast-file storage on speakers.
- Enterprise high availability.

## 5. Technology Stack

### Backend

- Python
- FastAPI
- Uvicorn
- APScheduler
- SQLite
- Pydantic

### Frontend

- React
- Vite
- CSS / Tailwind CSS

### Audio

- FFmpeg
- RTP
- UDP multicast
- Windows Audio for the amplifier endpoint

### Realtime

- WebSocket

### Deployment

- Run directly on the existing Windows PC.
- Docker deferred until networking/audio behavior is proven.
- Architecture should remain portable to Linux later.

## 6. Core Audio Concept

RTP multicast should be treated conceptually as a **virtual network audio cable**.

```text
Audio File
    ↓
Windows PA Server
    ↓
Audio Processing
    ├──────────────► RTP Multicast ─────► IP Speakers
    │
    └──────────────► Windows Audio ─────► Amplifier ─────► Internal Speakers
```

One multicast stream can be consumed by multiple IP speakers.

Example test destination:

```text
239.10.10.10:5004
```

The address is only an example and must be verified against the actual network.

## 7. Functional Requirements

### FR-001 — Audio Library

Manage centrally stored audio:

- MP3
- WAV
- FLAC
- Other FFmpeg-supported formats

Metadata:

```text
id
filename
display_name
path
format
duration
size
created_at
updated_at
```

### FR-002 — Upload

Operator can upload audio through the dashboard.

The server validates, stores, and extracts metadata.

### FR-003 — Manual Playback

Operator can select an audio file and start playback.

Playback may target:

1. RTP multicast → IP speakers.
2. Windows Audio → existing amplifier.

### FR-004 — Stop

Operator can stop active playback.

```text
PLAY → STREAMING → STOP
```

### FR-005 — RTP Multicast

Configurable:

- Multicast IP.
- RTP/UDP port.
- Codec.
- Sample rate.
- Channels.
- Packetization parameters where required.

The exact codec/RTP parameters must be determined from the actual IP speaker firmware.

### FR-006 — Transcoding

FFmpeg handles source conversion.

```text
MP3/WAV
  ↓
FFmpeg
  ↓
Decode / Resample / Encode
  ↓
RTP
  ↓
Multicast
```

### FR-007 — Local Windows Audio

The server shall support:

```text
PA Server
  ↓
Windows Audio
  ↓
PC Audio Out
  ↓
Amplifier
  ↓
Internal Speakers
```

### FR-008 — Scheduler

Internal scheduler supports:

- Daily.
- Selected weekdays.
- One-time date/time.
- Enable/disable.

Example:

```text
07:00 — Daily   — Indonesia Raya
08:00 — Mon-Fri — Theme Song
17:00 — Mon-Fri — Theme Song
```

### FR-009 — Schedule Management

Operators can create, edit, delete, enable/disable, and view upcoming schedules.

### FR-010 — Playback Status

Dashboard should show:

- Current state.
- Current audio.
- Elapsed/duration.
- Multicast destination.
- Start time.
- Active schedule.
- Local output state.

### FR-011 — Logs

Record playback, scheduling, upload/delete, FFmpeg, stream, and recovery events.

### FR-012 — Free Alarm Clock Migration

During development:

- Keep Free Alarm Clock installed.
- Do not automatically modify its schedules.
- Avoid simultaneous playback from both systems.
- Test the new system independently.

Long-term target:

```text
Free Alarm Clock
       ↓
   replaced by
       ↓
PA Server Scheduler
```

## 8. Dashboard

### Main Control

```text
┌─────────────────────────────────────┐
│             PA CONTROL              │
├─────────────────────────────────────┤
│ ● STREAMING                         │
│ Indonesia Raya                      │
│ 01:14 / 02:10                       │
│                                     │
│ [ PLAY ]       [ STOP ]             │
│                                     │
│ RTP: 239.10.10.10:5004              │
│ Local Output: ON                    │
└─────────────────────────────────────┘
```

### Audio Library

```text
Indonesia Raya.wav       [Play]
Theme Song.mp3           [Play]
Announcement.wav         [Play]

[+ Upload Audio]
```

### Schedule

```text
07:00   Indonesia Raya    Daily
08:00   Theme Song        Mon-Fri

[+ Add Schedule]
```

## 9. Data Model

### AudioFile

```text
id
name
filename
path
format
duration
size
created_at
updated_at
```

### Schedule

```text
id
name
audio_file_id
schedule_type
time
date
days_of_week
enabled
created_at
updated_at
```

### PlaybackSession

```text
id
audio_file_id
status
started_at
stopped_at
source
error_message
```

### Settings

```text
multicast_address
multicast_port
codec
sample_rate
channels
timezone
audio_directory
local_audio_device
```

## 10. API Concept

```text
GET    /api/audio
POST   /api/audio
DELETE /api/audio/{id}

POST   /api/play
POST   /api/stop
GET    /api/playback

GET    /api/schedules
POST   /api/schedules
PUT    /api/schedules/{id}
DELETE /api/schedules/{id}

GET    /api/settings
PUT    /api/settings
```

WebSocket:

```text
/ws
```

Events:

```text
PLAYBACK_STARTED
PLAYBACK_STOPPED
PLAYBACK_ERROR
SCHEDULE_TRIGGERED
```

## 11. Existing Windows PC Strategy

The existing PC is preferred because it already has:

- Dedicated location.
- Network connectivity.
- Windows audio configuration.
- Amplifier connection.
- Existing alarm workflow.

### Migration

```text
CURRENT

Free Alarm Clock
      ↓
Windows Audio
      ↓
Amplifier
      ↓
Internal Speakers


PROTOTYPE

PA Server
      ├────► RTP Multicast ────► IP Speakers
      │
      └────► Windows Audio ────► Amplifier ────► Internal Speakers


FUTURE

PA Server
      ├────► RTP Multicast ────► IP Speakers
      │
      └────► Windows Audio ────► Amplifier ────► Internal Speakers

Free Alarm Clock retired
```

### Performance

Expected workload is lightweight:

- Python/FastAPI.
- SQLite.
- APScheduler.
- FFmpeg audio processing.
- RTP/UDP multicast.

A slow PC may make the dashboard feel less responsive, but a small number of audio streams should not require high-end hardware.

Priorities:

- Stable network.
- Stable Windows audio output.
- Disable sleep/hibernation.
- Reliable startup.
- Sufficient storage.
- UPS where available.

## 12. Prototype Roadmap

### Phase 0 — Network/audio validation

1. Use the existing Windows PC.
2. Connect one IP speaker to a test network.
3. Select an unused multicast address.
4. Determine supported speaker codec/RTP parameters.
5. Test a known-good RTP stream.
6. Test Windows local audio separately.
7. Verify the two output paths safely.

**Success:** test audio can be heard through the internal amplifier and/or one IP speaker without modifying the production SIP system.

### Phase 1 — Minimal streamer

```text
Audio File
    ↓
FFmpeg
    ├────► RTP Multicast ───► 1 IP Speaker
    │
    └────► Windows Audio ───► Amplifier
```

No web UI, database, or scheduler.

### Phase 2 — Multiple IP speakers

Use the same multicast destination for multiple speakers.

### Phase 3 — FastAPI playback API

```text
POST /api/play
POST /api/stop
GET  /api/playback
```

### Phase 4 — Audio Library

Upload, list, delete, metadata.

### Phase 5 — Scheduler

APScheduler + SQLite.

### Phase 6 — Dashboard

React interface for playback, library, schedules, status, and logs.

### Phase 7 — Hardening

- FFmpeg auto-restart.
- Network recovery.
- Process monitoring.
- Startup behavior.
- Configuration backup.
- Windows service/task startup.
- Power-loss recovery.

## 13. Reliability

If FFmpeg crashes:

```text
Crash → Detect → Log → Safe Restart
```

If network fails:

```text
Network failure → Detect → Log → Recover
```

Rules:

- Avoid duplicate FFmpeg processes.
- v0.1 has at most one normal broadcast stream.
- A failed RTP stream must not crash the scheduler/API.
- Local and network outputs must have predictable states.

## 14. Networking

Potential requirements:

- Multicast-capable switch.
- IGMP snooping where appropriate.
- Correct VLAN configuration.
- Firewall rules for RTP/UDP.
- No multicast address collision.

Use a dedicated test multicast address verified not to conflict with production.

## 15. Production Safety

The existing SIP/IP Phone/PA system must not be interrupted.

Testing should:

1. Use an isolated/test network where possible.
2. Start with one IP speaker.
3. Use an unused multicast address.
4. Avoid simultaneous Free Alarm Clock/new-system playback.
5. Avoid changing SIP settings unless required.
6. Keep the existing alarm workflow until migration is approved.

## 16. Success Criteria

- [ ] Existing Windows PC successfully hosts the prototype.
- [ ] Audio plays through the existing amplifier.
- [ ] One IP speaker receives RTP multicast.
- [ ] Multiple IP speakers receive the same stream.
- [ ] Broadcast files do not need to be stored on IP speakers.
- [ ] Manual Play/Stop works.
- [ ] Internal scheduler works.
- [ ] Scheduled playback starts automatically.
- [ ] Logs are available.
- [ ] FFmpeg failure can recover.
- [ ] Free Alarm Clock can eventually be retired without losing required alarm functionality.

## 17. Future Features

- Emergency priority.
- Microphone announcement.
- Text-to-speech.
- Multiple zones.
- Per-speaker targeting.
- Multiple multicast channels.
- Live microphone → RTP.
- SIP/IP Phone integration.
- Playlists.
- Volume management.
- Speaker health monitoring.
- Device discovery.
- Authentication/RBAC.
- Playback history.
- Redundant server.
- Failover.

## 18. Design Principles

1. Centralized audio storage.
2. Existing Windows PC as the initial server.
3. Thin IP speaker endpoints.
4. One multicast stream per broadcast channel.
5. Local amplifier output is treated as another endpoint.
6. Separate control plane and audio plane.
7. Use FFmpeg instead of reinventing codecs.
8. Prove audio/network behavior before building UI.
9. Do not disturb production systems.
10. Avoid overengineering v0.1.

## 19. MVP Definition

The smallest useful prototype is:

```text
Existing Windows PC
       │
       ├── Audio File
       ├── FFmpeg
       └── RTP Multicast
              │
              └────► 1 IP Speaker
```

In parallel:

```text
Audio File
   ↓
Windows Audio
   ↓
Amplifier
   ↓
Internal Speakers
```

After the audio path is proven:

```text
Python + FastAPI
+ SQLite
+ APScheduler
+ React
```

The first technical milestone is:

> **Make the existing Windows PC generate test audio, play it through the existing amplifier, and make one IP speaker receive the same test audio through RTP multicast.**
