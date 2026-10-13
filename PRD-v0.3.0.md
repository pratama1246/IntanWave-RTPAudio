# PRD — IP Audio PA System (Port & Maritime Operations)

**Version:** 0.3.0  
**Status:** Approved Specification  
**Context:** Marine Terminal & Port Operations (Pelabuhan)  
**Primary Deployment:** Windows Environment (Cross-Platform / Linux-ready architecture)

---

## 1. Executive Summary & Context

Sistem ini adalah **Centralized IP Audio Public Address (PA) & Broadcast System** yang dirancang khusus untuk lingkungan operasional **Pelabuhan**. Sistem ini menggantikan pemutaran alarm/audio manual yang terfragmentasi (sebelumnya menggunakan *Free Alarm Clock* pada PC Windows dan file audio lokal yang tersimpan terpisah di tiap unit IP Speaker).

Sistem baru menyatukan kontrol pemutaran, penjadwalan otomatis (K3 rutin, apel, lagu kebangsaan), serta transmisi audio langsung ke dua jalur keluaran fisik secara serempak tanpa latensi yang mengganggu.

---

## 2. Peta Perangkat & Topologi Jaringan

```text
                      [ CENTRAL AUDIO SERVER ]
                     Python (FastAPI) + SQLite
                     Web Dashboard (Operator)
                                 │
                     FFmpeg Streamer Engine
                                 │
       ┌─────────────────────────┴─────────────────────────┐
       │ (RTP Multicast 239.255.0.1:5004)                   │ (LAN Audio Stream / Direct)
       ▼                                                   ▼
┌───────────────────────────────┐               ┌─────────────────────────────────┐
│     NETWORK SWITCH (LAN)      │               │     PC ALARM CLIENT (Windows)   │
└──────────────┬────────────────┘               └────────────────┬────────────────┘
               │                                                 │ (Analog 3.5mm Jack)
    ┌──────────┴──────────┐                                      ▼
    ▼                     ▼                               ┌───────────────┐
[ IP SPEAKER 1 ]   [ IP SPEAKER 2..N ]                    │   AMPLIFIER   │
 Tonmind CS20       Tonmind CS20                          └───────┬───────┘
 (Area Dermaga)     (Area Gate/Yard)                              ▼
                                                        [ SPEAKER KANTOR ]
```

### Karakteristik Endpoint:
1. **IP Speaker Lapangan (CS20 / Tonmind Ceiling/Horn):**
   * Menerima audio jaringan melalui protokol **RTP Multicast** (`239.255.0.1:5004`).
   * Tidak lagi menyimpan file audio lokal di memori speaker yang terbatas (~2.7 MB).
2. **Speaker Kantor / Internal:**
   * Terhubung fisik melalui kabel analog dari soundcard PC Alarm ke unit Amplifier.
   * Dilayani oleh background client service pada PC Windows yang menyalurkan audio ke speaker kantor.

---

## 3. Core Functional Requirements (v0.3.0)

### FR-01: Centralized Audio Library
* Pengunggahan dan pengelolaan file audio berformat **MP3, WAV, FLAC, OGG**.
* Metadata otomatis: Judul, durasi, ukuran file, bitrate, dan format.
* Kategori audio operasional:
  * *Pengingat K3 & Safety Maritim* (Wajib APD, batas kecepatan truk, safety lifting crane).
  * *Seremonial & Rutin* (Indonesia Raya, Jingle Apel Pagi/Sore).
  * *Pemberitahuan Khusus* (Briefing operasional, cuaca maritim).

### FR-02: Precision Scheduler (APScheduler Engine)
* Penjadwalan akurat berbasis waktu lokal:
  * **Harian (Daily)**: Contoh: 07:00 Lagu Indonesia Raya.
  * **Hari Kerja (Mon–Fri)**: Contoh: 08:00 Jingle Jam Kerja, 16:30 Apel Sore.
  * **Interval Berkala**: Pengingat K3 otomatis setiap 2 jam sekali pada jam kerja.
  * **Satu Kali (One-Time)**: Tanggal & jam tertentu untuk kegiatan seremonial atau latihan tanggap darurat.
* Toggle aktif/nonaktif per jadwal tanpa perlu menghapus item.

### FR-03: Dual Output Orchestration (FFmpeg Transcoding)
* Sekali tombol *Play* ditekan atau jadwal terpicu, engine FFmpeg memproses:
  * Transcode audio ke format RTP standar (PCMA / G.711a atau PCMU / Opus).
  * Pancaran UDP Multicast ke alamat `239.255.0.1:5004`.
  * Penyaluran ke driver audio Windows lokal (PC Alarm) untuk diteruskan ke amplifier kantor.
* Tombol **Emergency STOP** global untuk mematikan seluruh audio seketika jika ada interupsi darurat.

### FR-04: Realtime Telemetry & WebSockets
* Dashboard terhubung via WebSocket (`/ws/status`) untuk menampilkan:
  * Status engine (*IDLE*, *STREAMING*, *ERROR*).
  * Judul audio aktif, elapsed time, total duration, dan visual progress.
  * Status output: RTP Multicast (Online) & Amplifier Kantor (Online).
  * Log aktivitas operasional terkini.

---

## 4. UI/UX Design Direction: "Industrial Maritime Dispatch Console"

### Konsep Estetika:
* **Anti-AI Slop**: Menghindari gradien ungu-pink, efek kaca buram (*glassmorphism*) berlebihan, atau template SaaS generik.
* **Bukan Flat Monoton**: Bukan sekadar tabel putih bootstrap datar yang membosankan.
* **Inspirasi**: Konsol dispatch modern pelabuhan/maritim (perpaduan hardware rack-mount broadcast profesional dengan UI web responsif yang presisi dan taktis).

### Elemen Kunci Desain:
1. **Palette Warna (Maritime Industrial)**:
   * **Chassis Background**: Deep Navy Slate (`#0B132B` / `#0F172A`) — kontras tinggi, nyaman di mata operator shift malam.
   * **Console Surfaces**: Solid Milled Dark Steel (`#1E293B`, `#334155`) dengan subtle border lines (`#475569`).
   * **Status Accents**:
     * *Radio / Live Green* (`#10B981` / `#059669`) untuk status audio ONLINE / ACTIVE.
     * *Signal Amber* (`#F59E0B`) untuk jadwal berikutnya & timer standby.
     * *Emergency Orange-Red* (`#EF4444`) khusus untuk tombol STOP darurat & indikator alert.
2. **Audio Activity Telemetry (VU Meter Segmented)**:
   * Visualizer audio bergaya bar segmen LED fisik (hijau $\rightarrow$ kuning $\rightarrow$ merah) yang bergerak saat siaran berlangsung.
3. **Typography**:
   * *Display & Header*: Clean Industrial Sans (Inter / Space Grotesk).
   * *Data, Frekuensi & Jam*: Monospace Presisi (JetBrains Mono) untuk jam server, alamat IP `239.255.0.1:5004`, dan durasi hitung mundur.
4. **Tactile Controls**:
   * Tombol kontrol dengan *tactile press states* (efek klik fisik yang tegas).
   * Status badge menyerupai lampu indikator LED panel fisik.

---

## 5. Technology Stack

* **Backend**:
  * Python 3.14 (FastAPI + Uvicorn)
  * APScheduler (Background cron/interval scheduler)
  * SQLite (Database lokal `pa_system.db`, file-based, zero-maintenance)
  * Subprocess / FFmpeg bindings
* **Audio Engine**:
  * FFmpeg (Transcoder & RTP packetizer)
* **Frontend**:
  * React 18 / 19 + Vite
  * Tailwind CSS (Custom industrial tokens)
  * Lucide Icons (Minimalist industrial icons)
* **OS & Portabilitas**:
  * Native Windows host (environment saat ini).
  * Kode sepenuhnya kompatibel untuk migrasi ke Linux (Ubuntu Server / Debian) di masa depan tanpa refactoring logika inti.

---

## 6. Future Roadmap (Deferred Backlog)

Fitur berikut telah dipetakan dan disiapkan arsitekturnya, tetapi diimplementasikan setelah Phase MVP selesai:
1. **EWS (Early Warning System) Sirine Pelabuhan**:
   * 1 Tombol Sirine Evakuasi Bencana/Darurat dengan prioritas mutlak (override/cut-off audio rutin).
2. **SIP / IP Phone Speed-Dial Announcement**:
   * Integrasi IP Phone Control Room untuk live paging via SIP extension dial.
3. **Admin Live Mic Capture Tray Tool**:
   * Aplikasi client native ringan (mini-tray `.exe`) di laptop admin untuk broadcast mic/system audio secara langsung tanpa hambatan izin HTTPS browser.
4. **Multi-Zone Broadcasting**:
   * Pemisahan multicast address per zona (misal: Zona Dermaga vs Zona Perkantoran).

---

## 7. Success Criteria MVP

- [ ] FFmpeg terpasang dan dapat memancarkan RTP Multicast ke IP Speaker CS20 (`239.255.0.1:5004`).
- [ ] IP Speaker CS20 bersuara jernih menerima audio uji coba.
- [ ] PC Windows dapat memutar audio uji coba ke amplifier kantor secara bersamaan.
- [ ] Operator dapat mengunggah file MP3/WAV melalui web dashboard.
- [ ] Scheduler berhasil memicu pemutaran audio sesuai jam yang disetel tanpa intervensi manual.
- [ ] Tombol manual Play & Stop bekerja responsif dan memperbarui status di web dashboard secara realtime.
