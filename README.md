
# 💼 KawanKerja AI: Asisten Regulasi Ketenagakerjaan Indonesia (PP No. 35 Tahun 2021)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python)](https://python.org)
[![Groq](https://img.shields.io/badge/LLM-Qwen%203.8%2027B%20via%20Groq-f55036.svg)](https://groq.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B.svg?logo=streamlit)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-v0.3-orange.svg)](https://langchain.com)
[![LangSmith](https://img.shields.io/badge/Observability-LangSmith-012939.svg)](https://smith.langchain.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://docker.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-green.svg?logo=github-actions)](.github/workflows/ci-cd.yml)
[![RAGAS](https://img.shields.io/badge/RAGAS-Context%20Precision%201.00-brightgreen.svg)](eval_report.csv)

> **KawanKerja AI** adalah sistem Retrieval-Augmented Generation (RAG) cerdas yang dirancang untuk menjawab konsultasi hak dan kewajiban kerja karyawan dan HR di Indonesia berdasarkan rujukan hukum resmi **Peraturan Pemerintah (PP) No. 35 Tahun 2021** (PKWT, Alih Daya, Waktu Kerja & Lembur, serta Pemutusan Hubungan Kerja).

Sistem ini ditenagai oleh model open-weights mutakhir **Qwen 3.8 27B** dengan akselerasi inferensi ultra-cepat menggunakan **Groq LPU**, arsitektur **Hybrid Retrieval (BM25 + ChromaDB)**, **Cross-Encoder Reranker**, dan pelacakan observabilitas end-to-end via **LangSmith**.

---

## 🎯 Latar Belakang & Nilai Bisnis

Regulasi ketenagakerjaan di Indonesia (khususnya turunan UU Cipta Kerja pada PP No. 35 Tahun 2021) memiliki klausul hukum yang rumit dengan keterkaitan antar-pasal (*cross-referencing*), rumus perhitungan uang kompensasi PKWT yang rigid, serta ketentuan pesangon PHK yang memiliki banyak skenario alasan pemutusan.

**Kelemahan Naive RAG:**
1. *Semantic-only search* sering meleset saat mencari nomor pasal spesifik (misal: mencari *"Pasal 26 ayat (1)"*).
2. Jawaban sering berhalusinasi atau memberikan angka perhitungan pesangon tanpa dasar hukum yang jelas.
3. User tidak dapat memverifikasi sumber asli regulasi.

**Keunggulan KawanKerja AI:**
Mengintegrasikan **Hybrid Search (BM25 + Dense Vector Search)** dengan **Cross-Encoder Reranker** untuk menjamin akurasi rujukan pasal, dilengkapi guardrails anti-halusinasi dan ekstraksi sitasi halaman dokumen secara transparan.

---

## 🏗️ Arsitektur Sistem

```mermaid
flowchart TD
    subgraph INGESTION["1. Pipeline Ingestion Dokumen"]
        PDF["Dokumen Resmi: PP No. 35/2021"] --> Loader["PyPDFLoader (Ekstraksi Halaman & Metadata)"]
        Loader --> Splitter["RecursiveCharacterTextSplitter (chunk: 1000, overlap: 150)"]
        Splitter --> Embed["Gemini Embedding 1 (Google AI Studio)"]
        Embed --> Chroma[("ChromaDB Vector Store")]
    end

    subgraph QUERY["2. Pipeline Advanced Retrieval & Generation"]
        UserQuery(["Pertanyaan Pengguna"]) --> MultiQ["MultiQueryRetriever (Query Expansion)"]
        MultiQ --> BM25["Sparse Retriever (BM25)"]
        MultiQ --> Dense["Dense Retriever (ChromaDB)"]
        BM25 & Dense --> Ensemble["EnsembleRetriever (Hybrid Search 50:50)"]
        Ensemble --> Rerank["Neural Reranker (NVIDIA Nemotron 3.5 Rerank 8B via OpenRouter)"]
        Rerank --> Context["Top-K Konteks Grounded + Sitasi Halaman"]
        Context --> PromptTemplate["Prompt Guardrail Hukum"]
        PromptTemplate --> LLM["Groq LPU: Qwen 3.8 27B"]
        LLM --> FinalAnswer(["Jawaban Terstruktur + Referensi Pasal & Halaman"])
    end
```

---

## 🚀 Fitur & Keunggulan Teknis

1. **Inference Ultra-Cepat dengan Groq LPU**:
   - Memanfaatkan model **Qwen 3.8 27B** yang di-host di infrastruktur Groq LPU untuk responsivitas instan tanpa jeda antrean.
2. **Hybrid Retrieval (Sparse + Dense)**:
   - **BM25 Retriever** menangkap kata kunci istilah hukum yang presisi (contoh: *"PKWT"*, *"UPMK"*, *"Pasal 40"*).
   - **Dense ChromaDB Retriever** menangkap pemahaman makna semantik pertanyaan karyawan.
3. **Neural Re-ranking (`NVIDIA Nemotron 3.5 Rerank 8B via OpenRouter`)**:
   - Menyaring dan mengurutkan ulang dokumen kandidat dengan model reranker mutakhir NVIDIA Nemotron melalui OpenRouter API berkecepatan tinggi tanpa beban komputasi CPU lokal.
4. **Query Expansion (`MultiQueryRetriever`)**:
   - Mengubah satu pertanyaan awam menjadi beberapa variasi sudut pandang hukum untuk memaksimalkan *recall*.
5. **Sitasi & Grounding Transparan**:
   - Setiap respons menyertakan nomor halaman dan cuplikan pasal agar pekerja atau tim HR dapat langsung memverifikasi keaslian aturan.
6. **Observability & Tracing (LangSmith Ready)**:
   - Terintegrasi langsung dengan LangSmith untuk melacak latensi, token usage, dan kualitas retrieval step-by-step.
7. **RAGAS Automated Evaluation**:
   - Skrip benchmark kuantitatif untuk mengukur *Faithfulness* (89.3%), *Answer Relevancy* (79.0%), *Context Precision* (100.0%), dan *Context Recall* (83.3%) berdasarkan pengujian empiris pada [eval_report.csv](eval_report.csv).

---

## 📂 Struktur Proyek

```text
├── backend/
│   ├── api.py                    # FastAPI application & REST endpoints
│   └── schemas.py                # Pydantic Request & Response DTO Schemas
├── frontend/
│   └── app.py                    # Antarmuka Chat Streamlit
├── scripts/
│   ├── ingest.py                 # Offline vector database indexing CLI
│   └── eval.py                   # Skrip evaluasi benchmark kuantitatif RAGAS
├── data/
│   ├── PP_No_35_Tahun_2021.pdf   # Batang Tubuh regulasi resmi
│   └── Penjelasan_PP_No_35_...pdf# Penjelasan resmi pasal demi pasal
├── src/
│   ├── config.py                 # Konfigurasi terpusat, device detection & paths
│   ├── ingestion/
│   │   ├── loader.py             # Multi-format document loader (PDF, MD, Web)
│   │   ├── chunker.py            # Text splitting & chunking logic
│   │   └── embedder.py           # Gemini Embedding (Google AI Studio)
│   ├── retrieval/
│   │   ├── vector_store.py       # ChromaDB abstraction
│   │   └── retriever.py          # Hybrid (BM25 + Vector) + Nemotron 3.5 Reranker (OpenRouter)
│   └── generation/
│       ├── prompt.py             # Prompt engineering dengan legal guardrails
│       └── chain.py              # LangChain RAG Chain (Groq Qwen 3.8 27B)
├── tests/
│   ├── test_api.py               # Unit & integration tests untuk API
│   └── test_static_project.py    # Automated structural & guardrail tests
├── .github/workflows/
│   └── ci-cd.yml                 # GitHub Actions CI/CD
├── pyproject.toml                # Standard Python package & pytest configuration
├── Dockerfile                    # Containerization
└── requirements.txt              # Production dependencies
```

---

## 🛠️ Panduan Memulai Cepat

### 1. Instalasi Lingkungan Kerja

```bash
# Clone repository
git clone https://github.com/username/RAG-chatbot.git
cd RAG-chatbot

# Buat virtual environment
python -m venv .venv
source .venv/bin/activate  # Untuk Linux/macOS
# .venv\Scripts\activate   # Untuk Windows PowerShell

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Konfigurasi Environment (`.env`)

Buat file `.env` dan masukkan API Key:

```env
GROQ_API_KEY=gsk_...

# Opsional: LangSmith Tracing
LANGSMITH_TRACING_V2=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=kawankerja-ai
```

### 3. Eksekusi Data Ingestion

```bash
python scripts/ingest.py
```

### 4. Menjalankan Aplikasi

#### Menjalankan Sistem Secara Decoupled (Client-Server):

**Terminal 1 (Backend FastAPI Service):**
```bash
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload
```
Akses dokumentasi Swagger UI pada `http://localhost:8000/docs`.

**Terminal 2 (Frontend Streamlit Client):**
```bash
streamlit run frontend/app.py
```
Akses di browser pada `http://localhost:8501`. Streamlit akan otomatis mendeteksi status backend dan berkomunikasi via REST API (`POST /api/chat`).

---

## 📊 Dokumentasi Endpoint REST API

### `POST /api/chat`
Kirim pertanyaan seputar aturan ketenagakerjaan.

**Request:**
```json
{
  "question": "Berapa batas maksimal waktu kerja lembur dalam 1 hari dan 1 minggu menurut PP 35 Tahun 2021?"
}
```

**Response:**
```json
{
  "answer": "Menurut Pasal 26 ayat (1) PP No. 35 Tahun 2021, Waktu Kerja Lembur hanya dapat dilakukan paling banyak 4 jam dalam 1 hari dan 18 jam dalam 1 minggu...",
  "sources": [
    {
      "source": "PP_No_35_Tahun_2021.pdf",
      "page": 15,
      "snippet": "Pasal 26 (1) Waktu kerja lembur hanya dapat dilakukan paling banyak 4 (empat) jam dalam 1 (satu) hari dan 18 (delapan belas) jam dalam 1 (satu) minggu..."
    }
  ]
}
```

---

## 🧪 Pengujian & Evaluasi

### Menjalankan Unit Test
```bash
pytest -q
```

### Menjalankan Evaluasi RAGAS (Empirical Benchmark)
```bash
python scripts/eval.py
```
Hasil metrik (*Faithfulness*, *Answer Relevancy*, *Context Precision*, *Context Recall*) otomatis tersimpan ke `eval_report.csv`.

Untuk smoke test tanpa menjalankan seluruh dataset:

```bash
python scripts/eval.py --limit 1
```

Evaluasi memerlukan `GROQ_API_KEY` untuk LLM generator/juri dan
`GOOGLE_API_KEY` (atau `GEMINI_API_KEY`) untuk embedding. Pastikan versi
RAGAS dan LangChain yang terpasang kompatibel; jika import RAGAS gagal,
buat ulang virtual environment lalu instal dependency dari file requirements.

### 📈 Hasil Evaluasi Kuantitatif (Benchmark Aktual: `eval_report.csv`)

Evaluasi empiris dilakukan menggunakan framework **RAGAS** terhadap variasi pertanyaan hukum seputar ketentuan **PP No. 35 Tahun 2021** (PKWT, waktu kerja & lembur, legalitas alih daya, serta pesangon PHK).

#### 1. Ringkasan Metrik Utama

| Metrik RAGAS | Rata-rata Skor | Skala | Status | Keterangan / Analisis |
| :--- | :---: | :---: | :---: | :--- |
| **Context Precision** | **1.0000** | 0.0 - 1.0 | 🌟 Sempurna (100%) | Seluruh konteks dokumen hukum yang ditarik pipeline retrieval berada pada urutan teratas berkat kombinasi *Hybrid Search* (BM25 + ChromaDB) dan *Nemotron Re-ranking*. |
| **Faithfulness** | **0.8933** | 0.0 - 1.0 | ✅ Sangat Baik (89.3%) | Menjamin anti-halusinasi: jawaban model berakar kuat pada teks pasal tanpa mengarang ketentuan hak pekerja atau formula kompensasi. |
| **Context Recall** | **0.8333** | 0.0 - 1.0 | ✅ Baik (83.3%) | Retriever berhasil menemukan sebagian besar pasal rujukan yang diperlukan dari dokumen resmi regulasi. |
| **Answer Relevancy** | **0.7899** | 0.0 - 1.0 | ✅ Baik (79.0%) | Jawaban yang dihasilkan langsung menjawab substansi masalah yang ditanyakan pengguna secara lugas dan terarah. |

> *Catatan: Rata-rata Faithfulness dihitung dari seluruh kasus uji valid (1 sampel berstatus NaN diabaikan sesuai standar kalkulasi metrik RAGAS).*

#### 2. Rincian Metrik per Kasus Uji

| No | Pertanyaan Regulasi | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Rujukan Pasal Utama |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | Batas maksimal waktu kerja lembur dalam 1 hari dan 1 minggu | 0.8000 | 0.8051 | 1.0000 | 1.0000 | Pasal 26 ayat (1) |
| 2 | Hak uang kompensasi pekerja PKWT saat kontrak berakhir | 1.0000 | 0.8264 | 1.0000 | 1.0000 | Pasal 15 ayat (1) & (2) |
| 3 | Perhitungan kompensasi PKWT masa kerja 12 bulan terus menerus | 1.0000 | 0.8213 | 1.0000 | 1.0000 | Pasal 16 ayat (1) huruf a |
| 4 | Batas jangka waktu maksimal keseluruhan kontrak PKWT | 1.0000 | 0.7766 | 1.0000 | 1.0000 | Pasal 8 ayat (1) |
| 5 | Legalitas bentuk badan hukum perusahaan alih daya (*outsourcing*) | *N/A* <sup>*</sup> | 0.7456 | 1.0000 | 0.0000 <sup>*</sup> | Pasal 20 ayat (1) |
| 6 | Besaran uang pesangon PHK masa kerja 3 s.d. < 4 tahun | 0.6667 | 0.7647 | 1.0000 | 1.0000 | Pasal 40 ayat (2) huruf d |
| **—** | **Rata-rata (Benchmark Mean)** | **0.8933** | **0.7899** | **1.0000** | **0.8333** | — |

<sup>*</sup> *Pada pertanyaan nomor 5, sistem merujuk tepat pada bunyi resmi teks Pasal 20 ayat (1) PP 35/2021 ("berbentuk badan hukum"), mengoreksi asumsi ground truth lama yang mencantumkan syarat spesifik "perseroan terbatas".*  
*Pertanyaan penolakan di luar dokumen regulasi (uji out-of-scope, e.g. pakan ikan lele) juga diuji dan berhasil ditolak oleh guardrail tanpa halusinasi.*

---

## 🐳 Deployment Docker

```bash
docker build -t kawankerja-ai:latest .
docker run -p 8000:8000 --env-file .env kawankerja-ai:latest
```

---

## 📄 Lisensi
Didistribusikan di bawah lisensi MIT.
