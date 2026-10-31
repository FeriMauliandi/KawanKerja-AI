import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.config import DEFAULT_SOURCES, CHUNK_SIZE, CHUNK_OVERLAP
from src.ingestion.loader import load_data
from src.ingestion.chunker import split_documents
from src.ingestion.embedder import get_embedding_model
from src.retrieval.vector_store import get_vector_store

SOURCES = DEFAULT_SOURCES


def run_ingestion_pipeline(sources=None, reset_db: bool = True):
    if sources is None:
        sources = DEFAULT_SOURCES

    print("=================================================================")
    print("Memulai Data Ingestion Pipeline untuk PP No. 35 Tahun 2021")
    print("Provider Embedding: Google AI Studio (Gemini Embedding 1, 768-dim)")
    print("=================================================================\n")
    all_chunks = []
    
    for source in sources:
        try:
            raw_docs = load_data(source)
            chunks = split_documents(raw_docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            all_chunks.extend(chunks)
            print(f"Berhasil memproses: {Path(source).name} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"Gagal memproses {source}: {e}")
            
    if all_chunks:
        print(f"\nMenyiapkan model Gemini Embedding dan menyimpan {len(all_chunks)} chunks ke ChromaDB...")
        embedder = get_embedding_model()
        get_vector_store(chunks=all_chunks, embedding_model=embedder, reset=reset_db)
        print("\nSelesai! Semua data regulasi PP 35/2021 berhasil diindeks dan siap digunakan untuk RAG.")
    else:
        print("\nTidak ada data yang berhasil diproses.")


if __name__ == "__main__":
    run_ingestion_pipeline()
