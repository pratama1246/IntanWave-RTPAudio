# 🔊 IntanWave — Industrial IP Speaker & Maritime Public Address (PA) System

[![Docker Support](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](#-linux-server-deployment-docker-compose)
[![Python FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React Vite](https://img.shields.io/badge/React%2019-Vite%208-61DAFB?logo=react&logoColor=black)](https://vitejs.dev)
[![RTP Multicast](https://img.shields.io/badge/Audio-RTP%20Multicast%205004-FF6F00)](#-physical-ip-speaker-configuration)
[![Memory Limit](https://img.shields.io/badge/RAM%20Limit-150MB-green)](#-docker-resource-limits)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**IntanWave** is a centralized, industrial-grade IP Public Address (PA) and automated audio broadcast system engineered specifically for maritime ports, cargo terminals, warehouses, and industrial facilities. It delivers synchronized, zero-buffer, multi-zone audio directly to physical IP horn speakers (e.g. Tonmind CS20, SIP/RTP horn speakers) using **RTP Multicast (`239.255.0.1:5004`)** and targeted **Unicast RTP** streams.

---

## 🌟 Key Features

### 🎵 High-Performance RTP Streaming Engine
- **Telecom-Standard Audio (8 kHz G.711 A-Law Mono)**: Direct VoIP/RTP multicast and unicast streaming encoded on-the-fly via FFmpeg for industrial IP speakers.
- **20ms Strict Frame Slicing**: Audio filters apply strict sample pacing (`aresample=8000:async=1,asetnsamples=n=160`) to eliminate drift and intermittent dropouts on long multi-minute broadcasts.
- **Locked 172-Byte Datagrams**: RTP payloads are packetized at 160 bytes audio + 12 bytes header (`?pkt_size=172`) matching IP speaker DSP jitter buffers.

### 🛡️ Multi-Zone Parallel Streaming & Anti-Echo Muxing
- **Parallel Multi-Zone Streaming**: Non-overlapping speaker zones play simultaneously without interrupting each other.
- **Shared-SSRC Tee Muxing**: Transmits simultaneous unicast/multicast outputs using a coordinated SSRC (`ssrc={shared_ssrc}:seq=0`) to eliminate echo.
- **Target Deduplication**: Automatic deduplication of target endpoints across overlapping groups.
- **Priority Queue**: Higher-priority broadcasts (Darurat/Emergency) cleanly preempt lower-priority audio; concurrent automated schedules wait in a FIFO queue until speakers are free.

### 🚨 Emergency Warning System (EWS)
- **Instant Evacuation Siren**: Dedicated red alert trigger to broadcast emergency sirens across all terminals with zero latency.
- **Broadcast Confirmation Modal**: An explicit confirmation dialog precedes manual playback from the Audio Library table to prevent accidental live broadcasts.

### ⏰ Multi-Time Group Broadcast Scheduler
- **Multiple Broadcast Times per Rule**: Configure single rules with several trigger points (e.g., `07:30`, `11:45`, `14:00`, `16:56`) rendered as high-contrast time badges.
- **Shift Presets**: Quick-fill buttons for common port routines (Morning Muster, Rest Breaks, Shift Closing).
- **Dynamic Nearest Countdown**: Live countdown card continuously tracks and displays the time remaining until the next upcoming broadcast.

### 📡 Real-Time Telemetry & Health Monitoring
- **Parallel Asynchronous ICMP Ping**: Continuous background ping monitoring tracking latency and online/offline states across all physical IP speakers.
- **WebSocket Live State Push**: Telemetry, playback state, and schedules update instantaneously across connected browser consoles without page reloads.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Control["📡 Central Broadcast Server (Port 7080)"]
        WebUI["Web Management Console (React 19 + Tailwind)"] -->|REST / WebSocket| API["FastAPI Backend Engine"]
        API --> Scheduler["APScheduler (Multi-Time Grouping)"]
        API --> DB[(SQLite pa_system.db)]
        API --> Streamer["FFmpeg RTP Engine (G.711 A-law 8kHz)"]
    end

    subgraph Network["🌐 Local Network Infrastructure (LAN / VLAN)"]
        Streamer -->|8kHz G.711 A-Law 20ms| MC["RTP Multicast 239.255.0.1:5004"]
        Streamer -.->|RTP Unicast Direct| UC["Unicast IP Endpoints (10.6.3.x:5004)"]
    end

    subgraph Endpoints["🔊 Physical IP Speakers (Tonmind CS20 / SIP Horns)"]
        MC --> Spk1["Dermaga 1–6 Berth Horns"]
        MC --> Spk2["RTK Yard Horns"]
        MC --> Spk3["Wijayapura & Kantor Horns"]
        UC --> Spk1
        UC --> Spk2
        UC --> Spk3
    end
```

---

## 📁 Repository Structure

```text
IntanWave-RTPAudio/
├── backend/                       # Primary Backend (Python FastAPI + SQLite + APScheduler)
│   ├── app/
│   │   ├── audio_engine.py        # RTP stream engine (8kHz G.711 A-law), multi-zone tee muxing, priority queue
│   │   ├── config.py              # Environment configurations, port mappings, storage paths
│   │   ├── database.py            # SQLite schema migrations, speaker definitions, audit logging
│   │   ├── main.py                # REST & WebSocket API, /api/health, speaker management
│   │   ├── ping_service.py        # Parallel ICMP ping engine & latency telemetry
│   │   └── scheduler.py           # APScheduler engine with multi-time trigger support
│   ├── requirements.txt           # Python backend dependencies
│   └── storage/audio/             # Central repository for audio WAV/MP3 files
├── frontend/                      # Web Management Console (React 19 + Vite 8 + Tailwind)
│   ├── src/
│   │   ├── App.jsx                # UI components, confirmation modals, multi-time scheduler
│   │   ├── index.css              # Industrial styling, truncation utilities, status indicators
│   │   └── main.jsx               # React DOM entrypoint
│   ├── package.json               # Node.js dependencies
│   └── vite.config.js             # Vite build configuration
├── Dockerfile                     # Multi-stage container build (Node builder + Python FFmpeg runner)
├── docker-compose.yml             # Docker compose specification with host networking & 150MB RAM limit
├── deploy-linux.sh                # Automated 1-step deployment script for Linux servers
├── run_server.py                  # Local development server launcher (Port 7080)
└── LICENSE                        # MIT License
```

---

## 🚀 Server Deployment Guide

### Option A: Linux Server Deployment (Docker Compose) — *Recommended*

The server operates on port **`7080`** by default. **Host networking mode** is utilized to ensure UDP Multicast datagrams egress directly onto physical network switches without container NAT interference.

```bash
# 1. Clone the repository
git clone https://github.com/pratama1246/IntanWave-RTPAudio.git
cd IntanWave-RTPAudio

# 2. Make deployment script executable
chmod +x deploy-linux.sh

# 3. Launch the automated deployment
./deploy-linux.sh
```

Or deploy directly using Docker Compose:
```bash
docker compose up -d --build
```

* **Web Console:** `http://<SERVER_IP>:7080`
* **Health Check API:** `http://<SERVER_IP>:7080/api/health`
* **Live Server Logs:** `docker compose logs -f`

#### 🛡️ Docker Resource Limits
To prevent noisy-neighbor memory exhaustion in multi-container production environments, the container is bounded by:
```yaml
mem_limit: 150m
mem_reservation: 64m
deploy:
  resources:
    limits:
      memory: 150M
    reservations:
      memory: 64M
```

---

### Option B: Local Bare-Metal Setup (Python)

Ensure **Python 3.10+**, **Node.js 20+**, and **FFmpeg** are installed and accessible in your system `PATH`.

```powershell
# 1. Build frontend bundle
cd frontend
npm install
npm run build
cd ..

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Launch server
python run_server.py
```
The console will be accessible at: `http://localhost:7080`

---

## 📻 Physical IP Speaker Configuration (e.g., Tonmind CS20)

To achieve flawless, uninterrupted playback on physical IP horn speakers:

1. Access your IP Speaker's web management interface.
2. Under **Audio Settings** / **RTP Multicast**, configure:
   * **Multicast IP**: `239.255.0.1`
   * **Port**: `5004`
   * **Audio Codec**: `PCMA (G.711 A-Law)`
   * **Sample Rate**: `8000 Hz`
   * **Priority**: `Priority 1` or `Priority 3` (per facility policy)
3. Under **Advanced / Hardware Settings**:
   * **Amp Auto OFF**: Set to **`NO`** *(prevents amplifier power-cycling on micro-silence)*.
   * **Jitter Buffer**: Set to **`360 ms`** or **`500 ms`** *(absorbs network jitter during multi-minute playback)*.
4. Save and apply settings.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `7080` | HTTP Web Console & REST/WebSocket API port |
| `MULTICAST_IP` | `239.255.0.1` | Target RTP Multicast Group IP address |
| `MULTICAST_PORT` | `5004` | Inbound/Outbound UDP Audio Port |
| `TZ` | `Asia/Jakarta` | Local system timezone for APScheduler routines |
| `FRONTEND_DIST` | `../frontend/dist` | Path to compiled static frontend assets |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
