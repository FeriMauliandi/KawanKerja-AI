import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.config import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSIONS, GOOGLE_API_KEY


def get_embedding_model(model_name: str = EMBEDDING_MODEL_NAME, api_key: str = None):
    """
    Menginisialisasi Google Generative AI Embeddings (Gemini Embedding)
    melalui Google AI Studio API.
    """
    # Normalisasi nama model jika user memasukkan alias lama
    normalized_name = model_name
    if normalized_name in ("embedding-001", "models/embedding-001"):
        normalized_name = "models/gemini-embedding-001"
    elif not normalized_name.startswith("models/"):
        normalized_name = f"models/{normalized_name}"

    key = api_key or GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "GOOGLE_API_KEY belum disetel di file .env! "
            "Silakan tambahkan GOOGLE_API_KEY=AIzaSy... ke dalam file .env Anda."
        )

    print(f"Mempersiapkan Gemini Embedding API: {normalized_name} (dim={EMBEDDING_DIMENSIONS})")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model=normalized_name,
        google_api_key=key,
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    
    return embeddings


# =======Blok testing=========
if __name__ == "__main__":
    embedder = get_embedding_model()
    
    teks_uji = "Mengubah teks regulasi hukum menjadi representasi vektor semantik dengan Gemini."
    vektor = embedder.embed_query(teks_uji)
    
    print("\n[BERHASIL]")
    print(f"Dimensi vektor (jumlah angka): {len(vektor)}")
    print(f"Cuplikan vektor 5 angka pertama: {vektor[:5]}")
