import os
from pathlib import Path
from dotenv import load_dotenv

# Load file environment (.env) jika tersedia
load_dotenv()

# Direktori utama proyek
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"

# Model konfigurasi default
LLM_MODEL_NAME = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")

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
    """Mendeteksi apakah akselerasi CUDA GPU tersedia untuk Embedding/PyTorch."""
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def get_reranker_device() -> str:
    """
    Menentukan device untuk Cross-Encoder Reranker.
    Menggunakan CPU jika VRAM GPU < 6GB untuk mencegah CUDA Out of Memory (OOM).
    """
    try:
        import torch
        if torch.cuda.is_available():
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if vram_gb >= 6.0:
                return "cuda"
            torch.cuda.empty_cache()
    except (ImportError, Exception):
        pass
    return "cpu"
