# IntanWave Node — C# Universal IP Audio Receiver

Klien audio receiver berbasis **C# (.NET 8 WPF)** dengan **Auto-Detection Sistem Operasi (Windows 8, Windows 8.1, Windows 10, dan Windows 11)**.

---

## ⚡ Fitur Utama

1. **Auto-Detect Windows Engine:**
   * **Windows 11:** Otomatis mengaktifkan **Native Mica Material & Rounded Corners**.
   * **Windows 10:** Mengaktifkan **Fluent Dark Mode**.
   * **Windows 8 & 8.1:** Menggunakan **Native Metro Theme (Flat Clean)** tanpa crash API modern.
2. **Native Audio Engine (Tanpa `ffplay.exe`):**
   * Menggunakan pipeline internal `NAudio` (WASAPI dengan fallback `WaveOutEvent` untuk driver audio lama Windows 8).
   * Mampu memutar file audio lokal dan streaming RTP Multicast G.711 A-law / mu-law langsung di memory.
   * Ukuran aplikasi sangat ringkas.
3. **Live Audio VU Meter:**
   * Indikator level audio real-time saat siaran berlangsung.
4. **Zero Server Modification:**
   * 100% kompatibel dengan server Python (`backend/app`) saat ini:
     * POST `/api/nodes/heartbeat`
     * GET `/api/nodes/{id}/schedules`
     * WebSocket `/ws/node/{id}`
     * Multicast RTP UDP `239.255.0.1:5004`
5. **System Tray & Single Instance:**
   * Bersembunyi rapi di System Tray dengan menu klik-kanan.
   * Proteksi instansi ganda (Global Mutex).

---

## 🚀 Cara Menjalankan

### Cara 1: Jalankan lewat batch script
```cmd
start_client.bat
```

### Cara 2: Jalankan via .NET CLI
```cmd
dotnet run --project IntanWave.Node.csproj
```

### Cara 3: Build Single-File Executable Standalone
```cmd
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true
```
Hasil publish akan berada di `bin\Release\net8.0-windows\win-x64\publish\IntanWave-Node.exe` yang bisa langsung dijalankan di PC manapun tanpa perlu instalasi runtime .NET!
