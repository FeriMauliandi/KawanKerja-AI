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
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Embedding: Google AI Studio Gemini Embedding 1
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))

# Reranker: NVIDIA Nemotron 3.5 Rerank 8B via OpenRouter
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL", "nvidia/nemotron-3.5-rerank-8b:free")

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
