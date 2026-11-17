# KawanKerja AI: Web Frontend

Antarmuka web modern, terstruktur, dan responsif untuk KawanKerja AI, asisten konsultasi regulasi hukum ketenagakerjaan Indonesia berbasis Peraturan Pemerintah (PP) No. 35 Tahun 2021.

Dibangun dengan HTML5, Tailwind CSS, dan Vanilla JavaScript (ES6+) tanpa ketergantungan build tool (zero-bundler / zero-build step), sehingga ringan, cepat, dan dapat langsung dijalankan di peramban mana pun.

## 1. Panduan Desain & Palet Warna (Cyber Emerald & Multi-Spectrum)

UI ini menerapkan panduan desain yang terdokumentasi pada `DESIGN.md` dengan identitas visual Cyber Emerald dan aksen tematik per kategori hukum:
* Warna Dasar (Background): `#00140f` (Deep Obsidian Emerald)
* Warna Permukaan Panel: `rgba(2, 33, 25, 0.85)` / `#022119`
* Warna Permukaan Kartu: `rgba(3, 46, 35, 0.70)` / `#032e23`
* Teks Utama: `#e0fff6` (Mint White Cyan, rasio kontras > 16:1 terhadap dasar)
* Teks Sekunder: `#80a89d` (Rasio kontras > 6:1 terhadap dasar)
* Aksen Utama: `#04e797` (Vibrant Legal Emerald untuk penegasan status dan tombol aksi utama)
* Multi-Spectrum Kategori Regulasi:
  * PKWT: `#06b6d4` (Cyan)
  * Kompensasi: `#04e797` (Emerald)
  * Lembur: `#f59e0b` (Warm Amber)
  * Pesangon PHK: `#f43f5e` (Rose Coral)
  * Pangkalan Data & Dokumen: `#6366f1` (Indigo)
  * Peringatan / Destruktif: `#ef4444` (Merah untuk pembatalan dan notifikasi kendala server)

## 2. Fitur Antarmuka

1. **Halaman Beranda (Landing Page) Terarah**:
   - Menjelaskan cakupan regulasi PP No. 35 Tahun 2021 (PKWT, kompensasi, jam lembur, dan pesangon PHK).
   - Pratinjau kasus nyata kompensasi PKWT masa kerja 8 bulan gaji Rp 6.000.000 dengan rujukan Pasal 15 ayat (1) dan (3) serta nomor halaman dokumen PDF asli.
   - Pilihan 4 kartu kategori kasus populer (PKWT, Kompensasi, Lembur, Pesangon PHK) dengan aksen warna tersendiri yang dapat langsung diklik untuk memulai konsultasi di chatbot.
   - Simulasi kalkulator kompensasi interaktif langsung di halaman depan.

2. **Hero Section dengan Kanvas Timbangan Keadilan**:
   - Kanvas animasi halus menggambarkan timbangan keadilan hukum ketenagakerjaan (Hak Pekerja dan Kepastian Hukum) yang seimbang.
   - 7 segel regulasi mengorbit dengan warna spektrum masing-masing (PP 35/2021, Pasal 8, Pasal 15, Pasal 26, Pasal 31, Pasal 40, Kepatuhan Regulasi).
   - Otomatis berhenti berputar jika pengguna mengaktifkan preferensi peramban `prefers-reduced-motion: reduce`.
   - Menggunakan `IntersectionObserver` agar animasi berhenti secara otomatis ketika bagian Hero tidak berada di area pandang layar.

3. **Ruang Konsultasi Chatbot**:
   - Area masukan mengambang di bagian bawah layar yang stabil dan tidak menggeser riwayat pesan saat jawaban dicetak.
   - Label formulir yang dapat diakses pembaca layar (screen reader) dan tombol pintas dengan atribut `aria-label` yang lengkap.
   - Tipografi formula matematika KaTeX yang rapi tanpa tanda kurung kurawal LaTeX mentah.
   - Riwayat percakapan multi-sesi yang tersimpan di `localStorage` peramban.
   - Dukungan masukan suara (Voice Input / Speech-to-Text) dan pembacaan teks suara (Text-to-Speech).
   - Fitur salin ke papan klip dan ekspor percakapan ke format Markdown (.md).

4. **Kalkulator Hak Ketenagakerjaan (Modal Interaktif)**:
   - Kompensasi PKWT (Pasal 15): Formula (Masa Kerja / 12) x 1 Bulan Upah.
   - Upah Lembur (Pasal 31 dan 32): Perhitungan upah per jam (1/173 x Upah) untuk hari kerja biasa dan hari libur resmi.
   - Estimasi Pesangon PHK (Pasal 40 sampai 59): Formula Uang Pesangon (UP) dan Uang Penghargaan Masa Kerja (UPMK) berdasarkan faktor pengali alasan PHK.
   - Modal dapat ditutup menggunakan tombol Escape pada keyboard atau tombol tutup yang tersedia.

5. **Aksesibilitas & Standar Antislop**:
   - Seluruh elemen interaktif memiliki kursor pointer dan fokus keyboard terlihat jelas (:focus-visible).
   - Bebas karakter em dash di seluruh antarmuka (R-02).
   - Target sentuh mobile memenuhi standar minimal 44x44px (R-03).
   - Kontras warna teks memenuhi standar WCAG AA (R-25).

## 3. Cara Menjalankan

### Cara 1: Menggunakan Python HTTP Server (Rekomendasi Standalone)
Buka terminal di root direktori proyek:
```bash
python -m http.server 3000 --directory frontend
```
Buka peramban di:
* http://localhost:3000 (Membuka Halaman Beranda)
* http://localhost:3000/#chat (Langsung ke Ruang Chatbot)

### Cara 2: Langsung Buka File index.html
Buka file `frontend/index.html` langsung di peramban web Anda.

### Cara 3: Melalui FastAPI Backend
Jika backend FastAPI dijalankan:
```bash
uvicorn backend.api:app --reload
```
Akses antarmuka di:
* http://127.0.0.1:8000/app

## 4. Struktur File

```text
frontend/
├── DESIGN.md          # Dokumen arah desain resmi (antislop direction)
├── index.html         # Landing Page & Chatbot App (Dual View SPA)
├── chat.html          # Pengalihan langsung ke ruang chat
├── css/
│   └── style.css      # Palet Cyber Emerald, glassmorphism, dan aksesibilitas
├── js/
│   ├── app.js         # Logika interaksi, kanvas, navigasi, dan REST client
│   └── calculator.js  # Modul kalkulator hak ketenagakerjaan PP 35/2021
├── app.py             # Implementasi antarmuka alternatif via Streamlit
└── README.md          # Dokumentasi teknis frontend
```
