# Panduan Desain KawanKerja AI

Dokumen arah desain (design direction) resmi untuk antarmuka web KawanKerja AI sesuai preferensi identitas pengguna dan standar antislop.

## 1. Identitas & Karakter Produk
* **Produk**: KawanKerja AI
* **Fungsi**: Asisten Yuridis Regulasi Ketenagakerjaan Indonesia (Peraturan Pemerintah No. 35 Tahun 2021)
* **Karakter Visual**: Cyber Emerald & Legal Tech terstruktur. Berwibawa, presisi, modern, dan berkepribadian kuat. Memadukan kedalaman Obsidian Emerald dengan spektrum aksen fungsional untuk setiap kategori hukum ketenagakerjaan.

## 2. Setelan Liveliness Dials
* **ENERGY: 2 (Balanced & Engaging)**. Nuansa tegas dan modern, kontras teks tinggi, aksen spektrum tematik yang terarah untuk membedakan instrumen hukum.
* **RHYTHM: 2 (Consistent with purposeful hierarchy)**. Alur naratif logis: Pembuka Hero -> Spesifikasi Teknis -> Pratinjau Penalaran Kasus Nyata -> 4 Topik Regulasi Populer -> Kalkulator Hak Mandiri -> Arsitektur Sistem RAG.
* **MOTION: 2 (Refined & Tactile)**. Animasi timbangan keadilan halus pada kanvas Hero, transisi hover kartu 200ms yang responsif, dan wajib mendukung `prefers-reduced-motion: reduce`.

## 3. Sistem Palet Warna (Cyber Emerald & Multi-Spectrum)
* **Warna Dasar (Background)**:
  * Obsidian Emerald: `#00140f` (Dasar utama ruang kanvas dan latar gelap mendalam)
* **Warna Permukaan (Surfaces)**:
  * Panel Glass: `rgba(2, 33, 25, 0.85)` / `#022119`
  * Card Surface: `rgba(3, 46, 35, 0.70)` / `#032e23`
  * Card Elevated / Hover: `rgba(5, 62, 48, 0.90)` / `#043e30`
  * Border Netral: `rgba(224, 255, 246, 0.08)`
  * Border Aksen Emerald: `rgba(4, 231, 151, 0.25)`
* **Tipografi & Kontras (WCAG AA 4.5:1+)**:
  * Teks Utama: `#e0fff6` (Mint White Cyan, rasio kontras > 16:1 terhadap dasar)
  * Teks Sekunder: `#80a89d` / `#a7f3d0` (Rasio kontras > 6:1 terhadap dasar)
* **Warna Inti & Identitas**:
  * Primary: `#04e797` (Vibrant Legal Emerald) untuk tombol tindakan utama, status aktif, dan aksen hero.
  * Primary Hover: `#03c681`
  * Royal Violet: `#480297` (Ambient glow sekunder di kanvas Hero)
  * Accent Fuchsia: `#a703b0`
* **Spektrum Kategori Regulasi Fungsional**:
  * PKWT (Perjanjian Kerja Waktu Tertentu): `#06b6d4` (Cyan)
  * Uang Kompensasi PKWT: `#04e797` (Vibrant Emerald)
  * Jam Kerja Lembur & Upah 1/173: `#f59e0b` (Warm Amber)
  * Pemutusan Hubungan Kerja (Pesangon PHK): `#f43f5e` (Rose Coral)
  * Pangkalan Dokumen Hukum & Sitasi: `#6366f1` (Indigo)
  * Peringatan / Destruktif: `#ef4444` (Merah untuk tombol stop dan pesan error)

## 4. Tipografi
* **Font Sans**: `'Plus Jakarta Sans', system-ui, -apple-system, sans-serif`
* **Font Mono**: `'JetBrains Mono', monospace` (untuk nomor pasal, formula matematis, nilai rupiah, dan sitasi)

## 5. Kaidah Antislop
* Bebas karakter em dash (`—`) di seluruh teks UI, komentar kode, dan dokumentasi (R-02).
* Data riil dan formula matematis resmi tanpa statistik palsu (R-23, R-38).
* Tidak ada elemen mati (dead controls): setiap tombol memiliki fungsi riil dan umpan balik jelas (R-32).
* Semua elemen interaktif memiliki `cursor: pointer`, state fokus keyboard terlihat (:focus-visible), dan dialog dapat ditutup dengan tombol `Escape` (R-26, R-32, R-39).
* Target sentuh mobile minimal 44x44px (R-03).
