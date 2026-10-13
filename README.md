# GoPA Audio System — Maritime Port PA & Broadcast Console

Centralized IP Audio Public Address (PA) System untuk lingkungan **Pelabuhan**. Sistem ini memancarkan siaran audio serentak ke **IP Speaker Tonmind CS20 (RTP Multicast)** dan ke **Speaker Kantor (Amplifier PC Alarm)**.

---

## 📁 Struktur Project

```text
audio-server-ip-speaker/
├── backend/                  # Server Utama (Python FastAPI + SQLite + APScheduler)
│   ├── app/                  # REST API, FFmpeg streamer engine, WebSocket
│   └── storage/audio/        # File audio MP3/WAV terpusat
├── frontend/                 # Web Dashboard (React + Vite + Tailwind, GoPay Style)
├── client-windows/           # Pure RTP Receiver Client untuk PC Alarm Windows
│   ├── app.py                # System Tray Icon + Mini Pop-up Widget
│   ├── receiver.py           # RTP Multicast Listener & Audio Output
│   ├── config.json           # Konfigurasi IP Multicast & Device Name
│   └── start_client.bat      # Launcher portable (tanpa jendela CMD)
├── PRD-v0.3.0.md             # Dokumen Spesifikasi Kebutuhan Sistem
├── DESIGN_SPEC.md            # Panduan Desain GoPay-Inspired Console
└── run_server.py             # Script utama untuk menjalankan Server + Web Dashboard
```

---

## 🚀 Panduan Menjalankan

### 1. Menjalankan Central Server (Web Dashboard)
Buka terminal dan jalankan:
```powershell
python run_server.py
```
* **Akses Dashboard Local:** [http://localhost:8000](http://localhost:8000)
* **Akses Dashboard dari LAN/HP:** `http://<IP-PC>:8000`

### 2. Menjalankan Windows Client (Di PC Alarm / Speaker Kantor)
Di PC Alarm yang terhubung ke amplifier:
1. Buka folder `client-windows/`
2. Cukup **double-click** file `start_client.bat`
3. Client akan langsung aktif dan standby di **System Tray** (dekat jam Windows).
4. Saat ada siaran masuk dari server, otomatis muncul **Push Notification Windows** dan suara langsung terdengar di speaker kantor!

---

## 📻 Konfigurasi IP Speaker CS20
Pada web admin IP Speaker CS20:
* Masuk ke menu **RTP Multicast**.
* Pada **Priority 1**, masukkan: `239.255.0.1:5004`
* Klik **Save**.
