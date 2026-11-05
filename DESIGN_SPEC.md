# Design specification — IntanWave

Diperbarui: 5 November 2026.

Dokumen ini menjelaskan desain yang sudah diterapkan di `frontend/src/App.jsx` dan `frontend/src/index.css`. Dokumen ini menggantikan spesifikasi tata letak sebelumnya.

## Arah visual

IntanWave adalah konsol siaran speaker IP untuk operator fasilitas dan pelabuhan. Antarmuka mengambil inspirasi dari perangkat audio fisik: bodi aluminium terang, layar charcoal yang cekung, serta tombol yang sedikit timbul.

Karakter utama:

- Hitam-putih dan abu netral sebagai dasar.
- Logo tetap memakai warna biru aslinya.
- Kedalaman dibuat dengan CSS, tanpa library atau model 3D.
- Warna tambahan menunjukkan kondisi operasional: koneksi, K3, dan darurat.
- Status, nama audio, tujuan, dan kontrol lebih diutamakan daripada elemen dekoratif.

Inspirasi bentuk perangkat: [Teenage Engineering TX–6](https://teenage.engineering/products/tx-6). Identitas produk tetap IntanWave.

## Tata letak

```text
Logo IntanWave                           Koneksi · Riwayat · Pengaturan

Ruang siaran.                                      Tanggal · Jam server

+-------------------------------------------+--------------------------+
| Pusat kendali audio                       | Jaringan speaker         |
| +---------------------------------------+ |                          |
| | Status · Judul audio · Tujuan          | | Jumlah perangkat online  |
| | Sesi aktif / antrean · Gelombang 3D    | | Ringkasan perangkat      |
| +---------------------------------------+ |                          |
| Siaran berikutnya         [Pilih audio]  | |                          |
| [Sirine] [K3] [Tujuan] / kontrol berhenti| | [Kelola perangkat]       |
+-------------------------------------------+--------------------------+

Jadwal & audio
[Jadwal siaran] [Pustaka audio]                    [Tambah / Unggah]
Jadwal berikutnya atau filter kategori
Tabel jadwal atau berkas audio

Footer
```

Header bersifat sticky. Bilah status siaran terpisah sudah dihapus; kontrolnya berada di panel utama. Jumlah speaker tidak diulang sebagai badge di header.

Pada desktop, panel utama menggunakan kolom fleksibel dan panel perangkat selebar 300 px. Pada lebar maksimal 900 px, kolom perangkat menjadi 260 px. Pada maksimal 720 px, kedua panel ditumpuk vertikal. Tabel tetap dapat digulir horizontal dalam wadahnya.

## Palet dan permukaan

| Elemen | Warna / perlakuan |
| --- | --- |
| Latar halaman | Abu netral `#e8e8e8` |
| Bodi panel | Gradien aluminium terang, garis tepi, highlight bagian atas |
| Layar siaran | Charcoal gelap, bingkai cekung, teks terang |
| Teks utama | Hitam atau abu gelap |
| Logo | Aset asli berwarna; tanpa filter grayscale |
| Status tersambung | Hijau dengan label teks |
| Aksi darurat | Merah dengan ikon dan label |
| Scrollbar | Thumb `#989898`, track `#e9e9e9`, hover `#777777` |

Gradien dan bayangan dipakai untuk menjelaskan bentuk permukaan serta respons tekan. Hindari menambahkan glow, glass, atau warna dekoratif ke setiap komponen.

## Panel siaran dan perubahan status

Warna yang berubah adalah **bodi luar panel**, sedangkan layar bagian dalam tetap gelap.

| Kondisi | Warna bodi atas → bawah | Label status |
| --- | --- | --- |
| Siaga | `#fdfdfd` → `#e6e6e6` | Sistem siaga |
| Siaran rutin | `#454545` → `#292929` | Sedang mengudara |
| K3 / keselamatan | `#fae6b4` → `#e9bd69` | Siaran keselamatan |
| Darurat | `#bc3048` → `#8d1830` | Siaran darurat |

Untuk beberapa sesi, kondisi mengikuti prioritas tertinggi: darurat, keselamatan, lalu rutin. Status juga ditulis sebagai teks agar tidak hanya mengandalkan warna.

- Tinggi panel tetap 440 px pada desktop dan 500 px pada lebar maksimal 720 px, baik saat siaga maupun siaran.
- Tinggi layar tetap 216 px. Judul maksimal dua baris; konten sesi panjang digulir di dalam layar.
- Transisi warna bodi, teks pendamping, border, dan bayangan berlangsung 0,5 detik dengan easing `ease`.
- Warna gradien dianimasikan melalui custom property bertipe warna, `--frame-top` dan `--frame-bottom`.
- Bentuk gelombang CSS bersifat dekoratif, bukan indikator level atau pengukur sinyal audio.
- Gelombang bergerak saat siaran aktif. Preferensi `prefers-reduced-motion` menonaktifkan animasi dan transisi.
- Sesi paralel menampilkan judul, tujuan, durasi, dan kontrol berhenti per sesi. Antrean menampilkan jumlah siaran yang menunggu.

## Tipografi dan ikon

- **DM Sans**: antarmuka, judul, label, dan tombol.
- **IBM Plex Mono**: jam, waktu siaran, angka teknis, dan counter.
- Font memiliki fallback sistem jika Google Fonts tidak tersedia.
- Gunakan sentence case dan istilah yang konsisten. Singkatan seperti RTP, K3, dan OPUS mengikuti penulisan resminya.
- Gunakan Lucide React untuk ikon; warna ikon boleh menunjukkan kategori dan status.
- Hindari teks promosi pada layar operator. Jelaskan tindakan dan akibatnya secara langsung.

## Tombol, filter, dan dropdown

Tombol aksi serta tombol ikon menggunakan highlight atas, bayangan pendek, dan efek turun saat ditekan. Tombol khusus seperti `hardware-key` dan filter kategori memiliki detail permukaan sendiri. Toggle serta baris daftar perangkat mempertahankan bentuk sesuai fungsinya.

- Tombol kategori berupa key abu-abu yang timbul. Kategori aktif terlihat cekung dan memiliki `aria-pressed`.
- Warna ikon K3 dan darurat membantu membedakan kategori tanpa mewarnai seluruh filter.
- Gunakan `CustomDropdown` untuk pilihan tunggal, termasuk codec. Pemilihan beberapa speaker memakai `MultiTargetSelector`.
- Scrollbar menu `CustomDropdown` disembunyikan, tetapi pengguliran tetap berfungsi.
- Tombol yang sedang menyimpan tetap menahan klik berulang. Tidak memakai cursor loading global.
- Pertahankan indikator fokus keyboard dan label aksesibel pada kontrol penting.

## Jadwal dan pustaka audio

Tab utama memisahkan jadwal dan pustaka. Tombol utama menyesuaikan tab: tambah jadwal atau unggah berkas.

Toggle jadwal memperbarui tampilan segera, menyimpan ke server, dan menahan klik berulang selama permintaan berlangsung. Pembaruan latar belakang tidak menimpa nilai yang masih disimpan. Jika penyimpanan gagal, status dikembalikan dan pengguna menerima pesan kesalahan.

Pustaka menyediakan filter Semua, Rutin, K3 & Safety, dan Darurat. Angka kategori berasal dari data aplikasi. Ikon pensil membuka perubahan nama dan prioritas audio.

## Modal dan konfirmasi

- Halaman belakang tidak dapat digulir selama ada modal terbuka, termasuk modal bertingkat.
- Isi modal tetap dapat digulir; tinggi maksimal 90dvh.
- Setelah seluruh modal ditutup, pengaturan scroll halaman dipulihkan.
- Scrollbar halaman dan modal berwarna abu-abu.
- Konfirmasi hapus jadwal, audio, speaker, dan grup menggunakan modal custom yang menyebut nama item, akibat penghapusan, serta pilihan Batal dan Hapus. Fokus awal berada pada Batal.
- Konfirmasi sirine menampilkan tujuan dan berkas suara. Tombol konfirmasi memulai countdown 5 detik; suara belum dikirim selama countdown.
- Countdown dapat dibatalkan dengan tombol batal atau menutup modal. Timer dibersihkan saat komponen dilepas. Pengiriman dimulai setelah hitung mundur selesai.

## Pengaturan codec

Pengaturan Sistem menyediakan satu codec aktif untuk siaran RTP dan tes speaker berikutnya: G.722, G.711A / PCMA, G.711U / PCMU, atau OPUS. Default mempertahankan G.722. Siaran yang sudah berjalan tidak diubah oleh pilihan baru.

Petunjuk harus menjelaskan bahwa codec penerima perlu disamakan. Untuk OPUS, tampilkan keterangan RTP payload type 111. Detail encoding dan pemetaan payload tercantum dalam README.

## Batas perubahan berikutnya

Pertahankan logo berwarna, panel siaran terpadu, ukuran panel yang stabil, serta kedalaman tombol. Jangan mengembalikan bilah status terpisah atau menambahkan kembali informasi yang sama di beberapa tempat tanpa kebutuhan operasional. Sesuaikan dokumentasi ini ketika tata letak atau perilaku komponen berubah.
