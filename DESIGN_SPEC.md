# Design Specification: IntanWave Audio Server

**Branding:** IntanWave  
**Prinsip Desain:** Bersih, fungsional, dan mengutamakan keterbacaan data penjadwalan.  
**Karakter Visual:** Antarmuka konsol audio profesional tanpa elemen dekoratif berlebihan, tanpa emoji, dan tanpa huruf kapital paksa.

---

## 1. Arsitektur Tata Letak

IntanWave menggunakan tata letak dua kolom seimbang agar seluruh fungsi penting dapat dipantau tanpa harus berpindah tab atau menggulir layar secara berlebihan:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│  INTANWAVE          RTP Multicast 239.255.0.1:5004    15:35:12 WIB    Pengaturan │
├──────────────────────────────────────────────────────────────────────────────────┤
│  STATUS SIARAN AKTIF                                                             │
│  Lagu Indonesia Raya • 01:24 / 02:30   [====================--------------]       │
│  Keluaran: Jaringan Multicast dan Soundcard Lokal                 [ Hentikan ]   │
├─────────────────────────────────────────┬────────────────────────────────────────┤
│  JADWAL SIARAN                          │  SIARAN CEPAT                          │
│                                         │                                        │
│  Siaran berikutnya: 16:25 Jingle Apel   │  [ Lagu Kebangsaan ]  [ Apel Masuk   ] │
│                                         │  [ Pengingat K3    ]  [ Himbauan Truk] │
│  [ Tambah Jadwal ]                      │  [ Istirahat Siang ]  [ Sirine Darurat]│
│                                         │  [ Unggah Berkas   ]  [ Kelola Berkas] │
│  08:08   Apel Pagi                AKTIF │                                        │
│          Setiap hari                    ├────────────────────────────────────────┤
│          Berkas: anthem_utama.mp3       │  STATUS PERANGKAT                      │
│                                         │                                        │
│  10:00   Lagu Kebangsaan          AKTIF │  Speaker CS20 Dermaga    Tersambung    │
│          Senin sampai Jumat             │  Speaker CS20 Gerbang    Tersambung    │
│          Berkas: lagu_kebangsaan.mp3    │  Terminal Audio Windows  Tersambung    │
│                                         │                                        │
│  16:56   Penutupan Jam Kerja   NONAKTIF ├────────────────────────────────────────┤
│          Setiap hari                    │  INFORMASI SISTEM                      │
│          Berkas: closing.mp3            │  Pustaka: 12 berkas audio              │
│                                         │  Jadwal aktif: 4 siaran                │
└─────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 2. Aturan Tipografi dan Gaya

* **Ketebalan Huruf:** Menggunakan `font-normal`, `font-medium`, dan `font-semibold`. Tidak menggunakan `font-extrabold` atau `font-black`.
* **Transformasi Teks:** Tidak menggunakan `uppercase`. Seluruh judul dan label ditulis menggunakan sentence case atau title case alami.
* **Spasi Karakter:** Menggunakan `tracking-normal`. Menghindari `tracking-wide` atau `tracking-wider`.
* **Ikon:** Menggunakan ikon vektor garis (Lucide React) monokrom. Tidak menggunakan karakter emoji.
* **Tanda Kurung:** Meminimalkan penggunaan teks di dalam tanda kurung agar salinan teks lebih ringkas dan terfokus.

---

## 3. Komponen Utama

### Bilah Siaran Aktif
Bilah horizontal kompak di bagian atas yang menampilkan status pemutaran audio secara realtime melalui WebSocket:
* Judul audio yang sedang mengudara.
* Counter durasi dan penunjuk kemajuan.
* Tombol darurat untuk menghentikan siaran seketika.

### Manajemen Jadwal Siaran
* **Banner Siaran Terdekat:** Menghitung jadwal berikutnya secara dinamis berdasarkan jam saat ini dan memberikan estimasi waktu tersisa.
* **Baris Jadwal:**
  * Waktu siar dalam angka jam digital berukuran besar dan mudah dibaca sekilas.
  * Keterangan siklus pemutaran harian atau hari kerja.
  * Sakelar aktif/nonaktif satu kali klik.
  * Tombol aksi untuk duplikasi jadwal, uji putar suara, dan hapus jadwal.

### Siaran Cepat
Papan tombol siaran instan untuk audio penting seperti bel masuk, himbauan keselamatan, atau sirine darurat yang dapat dipicu secara manual sewaktu-waktu.

### Status Perangkat
Daftar indikator endpoint penerima di jaringan lokal (RTP Multicast) dan soundcard komputer lokal yang terhubung ke amplifier.
