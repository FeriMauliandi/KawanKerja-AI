import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# API Keys Provider Eksternal
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Model konfigurasi default
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# Embedding: Google AI Studio Gemini Embedding 1
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Reranker: cross-encoder via OpenRouter /rerank (Cohere Rerank 3.5)
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL", "cohere/rerank-v3.5")
RERANKER_TIMEOUT = int(os.getenv("RERANKER_TIMEOUT", "8"))

# Strategi Retrieval (disesuaikan untuk korpus kecil: 2 PDF, ~101 chunk)
# Kandidat per retriever dibuat lebar karena 25 chunk masih ~25% korpus dan
# memberi ruang yang cukup untuk reranker memilih konteks terbaik.
RETRIEVAL_FETCH_K = int(os.getenv("RETRIEVAL_FETCH_K", "25"))
RETRIEVAL_RERANK_CANDIDATES = int(os.getenv("RETRIEVAL_RERANK_CANDIDATES", "20"))
RETRIEVAL_FINAL_K = int(os.getenv("RETRIEVAL_FINAL_K", "5"))
RETRIEVAL_BM25_WEIGHT = float(os.getenv("RETRIEVAL_BM25_WEIGHT", "0.45"))
RETRIEVAL_DENSE_WEIGHT = float(os.getenv("RETRIEVAL_DENSE_WEIGHT", "0.55"))
RETRIEVAL_EXACT_PASAL_WEIGHT = float(os.getenv("RETRIEVAL_EXACT_PASAL_WEIGHT", "1.25"))
RETRIEVAL_EXACT_PASAL_LIMIT = int(os.getenv("RETRIEVAL_EXACT_PASAL_LIMIT", "8"))
RETRIEVAL_MAX_PER_PAGE = int(os.getenv("RETRIEVAL_MAX_PER_PAGE", "2"))
# Pada 101 chunk, RRF + exact-pasal sudah memberi MRR yang sama dengan
# reranker, tetapi reranker menambah ~4 detik per query. Default dimatikan;
# aktifkan saat korpus bertambah besar atau saat presisi lebih penting.
RETRIEVAL_ENABLE_RERANKER = os.getenv(
    "RETRIEVAL_ENABLE_RERANKER", "false"
).lower() in ("1", "true", "yes", "on")
# Untuk korpus sekecil ini, query expansion via LLM tidak sepadan dengan
# latensi dan noise tambahannya. Aktifkan hanya jika korpus bertambah besar.
RETRIEVAL_ENABLE_QUERY_EXPANSION = os.getenv(
    "RETRIEVAL_ENABLE_QUERY_EXPANSION", "false"
).lower() in ("1", "true", "yes", "on")

# Konfigurasi Chunker & Ingestion
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

DEFAULT_SOURCES = [
    str(DATA_DIR / "PP_No_35_Tahun_2021.pdf"),
    str(DATA_DIR / "Penjelasan_PP_No_35_Tahun_2021.pdf"),
]

# Konfigurasi Server API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def get_device() -> str:
    """Mendeteksi ketersediaan device GPU/CPU (utilitas kompatibilitas)."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def get_reranker_device() -> str:
    """Device utilitas kompatibilitas (Reranker utama kini berjalan melalui OpenRouter API)."""
    return "cloud-api"
