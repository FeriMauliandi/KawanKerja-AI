# 💼 KawanKerja AI — Modern Web Frontend

Antarmuka web modern, elegan, dan responsif untuk **KawanKerja AI**, asisten konsultasi regulasi hukum ketenagakerjaan Indonesia berbasis **PP No. 35 Tahun 2021**.

Dibangun dengan **HTML5 + Tailwind CSS + Vanilla JavaScript (ES6+)** tanpa ketergantungan build tool (*zero-bundler* / *zero-build step*), sehingga ringan, cepat, dan langsung dapat dijalankan di lingkungan mana pun.

---

## 🎨 Palet Warna Cyber Emerald & Royal Neon

UI ini menggunakan palet warna khusus sesuai spesifikasi desain:
* `--background: #00140f;` (Deep Obsidian Emerald / Cyber Abyss)
* `--text: #e0fff6;` (Mint White Cyan yang sejuk dan tajam)
* `--primary: #04e797;` (Neon Emerald Green bercahaya)
* `--secondary: #480297;` (Deep Royal Violet)
* `--accent: #a703b0;` (Vibrant Magenta Fuchsia)

---

## ✨ Fitur Unggulan UI

1. **Halaman Landing Page Interaktif**:
   - Tampilan pembuka yang memperkenalkan kapabilitas RAG KawanKerja AI.
   - Papan metrik keandalan sistem (100% Grounded, <1s Groq LPU, Hybrid Retrieval, BAAI Reranker).
   - 4 Kartu Kasus Cepat: klik pertanyaan populer (PKWT, kompensasi, lembur, pesangon) untuk langsung membuka chatbot dengan pertanyaan terkirim.
   - Simulasi kalkulator kompensasi PKWT interaktif langsung di halaman depan.
   - Tombol *"Mulai Chatbot"* yang membawa pengguna mulus ke ruang konsultasi tanpa reload halaman.

2. **Page 1 Fullscreen Laptop & Animasi Yuridis (Scales of Justice & Legal Seals)**:
   - Page 1 (Hero Section) didesain **layar penuh (*fullscreen*) pada laptop & desktop** (`min-h-[calc(100vh-4.25rem)]`) dengan perataan vertikal yang simetris dan lega.
   - Menggunakan `<canvas id="legal-hero-canvas">` absolut yang **hanya aktif di Page 1**.
   - Menggambarkan **Timbangan Keadilan Hukum Ketenagakerjaan (Scales of Justice)** dinamis yang menyeimbangkan piringan *"HAK PEKERJA"* (Kompensasi Ps. 15 & Lembur Ps. 31) dan *"KEPASTIAN HUKUM"* (Kontrak PKWT Ps. 8 & Regulasi PP 35/2021).
   - Segel notaris resmi pasal-pasal kunci PP 35/2021 mengorbit lembut dengan garis vektor penyeimbang ke lengan timbangan.
   - Pola gelombang *guilloche security ribbon* khas sertifikat dan naskah Lembaran Negara RI.
   - Responsif terhadap kursor mouse di dalam Hero section dan otomatis berhenti (*IntersectionObserver*) saat pengguna menggulir ke seksi bawahnya.

3. **Seksi Khusus Pratinjau Konsultasi Nyata (Seksi 2 di Bawah Page 1)**:
   - Contoh hasil penalaran chatbot dipindahkan ke **Seksi 2 (`#pratinjau`)** tepat di bawah Page 1, sehingga Page 1 tetap bersih, berwibawa, dan tidak padat (*uncluttered*).
   - Menampilkan kasus simulasi nyata kompensasi PKWT masa kerja 8 bulan gaji Rp 6.000.000 dengan rincian pasal 15 ayat (1) & (3) serta rujukan halaman PDF resmi.

4. **Latar Belakang Bersih & Bebas 'AI Slop' Gradient**:
   - Menghilangkan *gradient radial blob* multi-warna yang artifisial, digantikan oleh tekstur kisi legal *micro-grid obsidian* (`#00140f`) yang tajam, formal, dan berwibawa.
   - Gelembung pesan pengguna bergaya *dark obsidian workstation* berbingkai mikro emerald yang tegas dan mudah dibaca.
   - Footnote sitasi naskah hukum resmi yang rapi dengan tautan verifikasi halaman dokumen PDF.

5. **Ruang Chatbot Modern & Floating Input**:
   - Form input mengambang (*floating overlay*) di bagian bawah layar yang **tidak tergeser** saat jawaban AI tercetak.
   - Gradien transparan di balik form input yang membuat percakapan meluncur lembut di latar belakang.
   - Tombol melayang *"Pesan Baru"* yang muncul otomatis saat pengguna menggulir ke riwayat lama.
   - Tombol navigasi *"Beranda"* untuk kembali ke Landing Page kapan saja.

3. **Rujukan Regulasi Resmi & Sitasi Terverifikasi Otomatis**:
   - Setiap respons AI selalu menyertakan rujukan hukum resmi (nama file PDF asli, nomor halaman dokumen, dan cuplikan pasal terkait).
   - Menampilkan konteks pertanyaan hukum yang telah disempurnakan (*conversational reformulation*) secara transparan.

4. **Kalkulator Hak Ketenagakerjaan (PP No. 35/2021)**:
   - **Kalkulator Kompensasi PKWT (Pasal 15)**: Formula $\frac{\text{Masa Kerja (Bulan)}}{12} \times \text{Upah}$.
   - **Kalkulator Upah Lembur (Pasal 31–32)**: Perhitungan upah per jam ($1/173 \times \text{Upah}$) untuk hari kerja biasa dan hari libur resmi.
   - **Kalkulator Estimasi Pesangon PHK (Pasal 40–59)**: Formula Uang Pesangon (UP) dan Uang Penghargaan Masa Kerja (UPMK) berdasarkan alasan PHK.

5. **Interaktivitas & Aksesibilitas**:
   - 🎙️ **Voice Input (Speech-to-Text)**: Ajukan pertanyaan langsung melalui mikrofon menggunakan Web Speech Recognition API bahasa Indonesia.
   - 🔊 **Text-to-Speech (TTS)**: Dengarkan penjelasan hukum AI dibacakan langsung oleh browser.
   - 📋 **Copy to Clipboard & Export Chat**: Salin jawaban dan unduh riwayat konsultasi dalam format Markdown (`.md`).
   - 💾 **Riwayat Percakapan Multi-Sesi**: Percakapan tersimpan rapi di `localStorage` peramban.
   - 🟢 **Live Backend Health Indicator**: Melacak ketersediaan dan latensi koneksi ke server FastAPI secara *real-time*.

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Python HTTP Server (Rekomendasi Standalone)
Buka terminal di root direktori proyek:
```bash
python -m http.server 3000 --directory frontend
```
Lalu buka browser di:
👉 **[http://localhost:3000](http://localhost:3000)** (Membuka Landing Page)  
👉 **[http://localhost:3000/#chat](http://localhost:3000/#chat)** (Langsung ke Chatbot)

### Cara 2: Langsung Buka File `index.html`
Cukup klik ganda file `frontend/index.html` di File Explorer Anda.

### Cara 3: Melalui FastAPI Backend
Jika backend FastAPI dijalankan:
```bash
uvicorn backend.api:app --reload
```
UI frontend dapat diakses langsung pada:
👉 **[http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)**

---

## 📂 Struktur File

```text
frontend/
├── index.html         # Landing Page & Chatbot App (Dual View SPA)
├── chat.html          # Redirect langsung ke ruang chat
├── css/
│   └── style.css      # Palet warna cyber emerald, glassmorphism & markdown prose
├── js/
│   ├── app.js         # Logika navigasi landing/chat, interaksi AI & state
│   └── calculator.js  # Modul kalkulator kompensasi, lembur, dan pesangon PP 35/2021
├── app.py             # Implementasi alternatif via Streamlit
└── README.md          # Dokumentasi teknis frontend
```
