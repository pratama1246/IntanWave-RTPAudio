# IntanWave Node — Universal IP Audio Receiver

Aplikasi client penerima audio jaringan multicast untuk **PC Windows** yang terhubung fisik ke amplifier speaker atau sound system lokal.

---

## ⚡ Ringan, Cepat & Universal
* **Nama Produk:** **IntanWave Node** (Bagian dari ekosistem *IntanWave Broadcast*).
* **Ukuran File:** Hanya **~14 MB** (standalone portable `.exe`, tidak perlu installer).
* **Pemakaian RAM:** Sangat irit (**~8.4 MB RAM**), tidak memberatkan sistem operasional PC.
* **Tampilan:** Menggunakan **Windows Default Native UI** (`Segoe UI`, kontrol asli Windows), bersih, responsif, dan rapi.
* **Single-Instance Protection:** Mencegah aplikasi dibuka ganda. Jika dibuka kembali, otomatis memunculkan kembali jendela yang sedang aktif.

---

## 💡 Fitur Utama

1. **Pure RTP Multicast Receiver:**
   * Otomatis mendengarkan paket audio RTP Multicast (`239.255.0.1:5004`).
   * Begitu console server menyiarkan audio (jingle/K3/pengumuman publik), audio langsung disalurkan ke amplifier speaker.
2. **Push Notifikasi Native Windows (Toast Notification):**
   * Banner pop-up Windows resmi *"IntanWave — Siaran Masuk"* muncul seketika di pojok kanan bawah saat siaran mengudara.
3. **System Tray Integration:**
   * Bersembunyi rapi di sebelah jam Windows (System Tray).
   * Klik icon tray untuk membuka Panel Kontrol atau klik kanan untuk menu cepat.
4. **Tes Bunyi Ampli:**
   * Tombol "Tes Bunyi Ampli" memutar nada bel ding-dong langsung ke soundcard amplifier untuk memastikan koneksi kabel & volume optimal.

---

## 🚀 Cara Menjalankan

### Cara 1: Double-Click File Executable (Rekomendasi)
Cukup double-click:
```text
IntanWave-Node.exe
```
*(atau jalankan via `start_client.bat`)*

### Cara 2: Lewat Script Python (Development)
```powershell
python app.py
```

---

## ⚙️ Cara Auto-Start Saat Windows Menyala (Booting)
1. Tekan `Win + R` di keyboard, ketik `shell:startup` lalu tekan Enter.
2. Buat **Shortcut** dari file `IntanWave-Node.exe` ke dalam folder Startup tersebut.
3. Sekarang setiap kali PC dinyalakan, IntanWave Node akan otomatis standby di System Tray!
