import os
import sys
import time
import shutil
from pathlib import Path
from typing import List

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import chromadb
from langchain_chroma import Chroma
from src.config import CHROMA_DB_DIR


def get_vector_store(
    chunks=None,
    embedding_model=None,
    persist_directory=None,
    collection_name: str = "langchain",
    reset: bool = False,
    batch_size: int = 25
):
    """
    Menyimpan chunks ke dalam ChromaDB atau memuat database jika sudah ada.
    Mendukung opsi reset bersih dan batching otomatis dengan mekanisme penanganan kuota
    rate-limit (100 RPM pada Google AI Studio Free Tier).
    """
    if persist_directory is None:
        persist_directory = str(CHROMA_DB_DIR)

    if embedding_model is None:
        raise ValueError("Model embedding harus disertakan!")

    persist_dir_path = Path(persist_directory)
    persist_dir_path.mkdir(parents=True, exist_ok=True)

    # Skenario 1: Menyimpan data baru (Ingestion)
    if chunks:
        if reset:
            print(f"Membersihkan koleksi '{collection_name}' di {persist_directory} untuk re-indexing bersih...")
            try:
                client = chromadb.PersistentClient(path=str(persist_directory))
                try:
                    client.delete_collection(collection_name)
                    print(f"Koleksi '{collection_name}' lama berhasil dihapus.")
                except Exception:
                    pass
            except Exception as e:
                print(f"[INFO] Catatan reset koleksi ChromaDB: {e}")

        vector_store = Chroma(
            collection_name=collection_name,
            persist_directory=str(persist_directory),
            embedding_function=embedding_model
        )

        total_chunks = len(chunks)
        print(f"Menyimpan {total_chunks} chunks ke dalam ChromaDB (batch size: {batch_size})...")

        for start_idx in range(0, total_chunks, batch_size):
            end_idx = min(start_idx + batch_size, total_chunks)
            batch = chunks[start_idx:end_idx]
            batch_num = (start_idx // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            print(f"  -> Mengindeks batch [{batch_num}/{total_batches}] (chunk {start_idx + 1}-{end_idx})...")

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    vector_store.add_documents(batch)
                    break
                except Exception as e:
                    err_msg = str(e).lower()
                    if ("429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg) and attempt < max_retries - 1:
                        wait_sec = 12 + (attempt * 3)
                        print(f"     [INFO] Batas kuota rate-limit Google AI Studio tercapai. Menunggu {wait_sec} detik sebelum mencoba kembali...")
                        time.sleep(wait_sec)
                    else:
                        raise e

            # Jeda singkat antar batch untuk menjaga pemakaian kuota rate limit tetap aman
            if end_idx < total_chunks:
                time.sleep(1.0)

        print("Semua data regulasi berhasil diindeks ke Vector Store!")
        return vector_store

    # Skenario 2: Membaca database yang sudah ada (Retrieval)
    else:
        if not persist_dir_path.exists():
            raise FileNotFoundError(
                f"Database vector belum ada di '{persist_directory}'. "
                "Silakan jalankan 'python scripts/ingest.py' terlebih dahulu!"
            )
            
        try:
            vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=str(persist_directory),
                embedding_function=embedding_model
            )
            return vector_store
        except Exception as e:
            if "dimension" in str(e).lower():
                raise RuntimeError(
                    "Dimensi database ChromaDB lama tidak cocok dengan model embedding baru. "
                    "Jalankan 'python scripts/ingest.py' untuk membangun ulang database secara otomatis."
                ) from e
            raise e


# ==========================================
# Blok testing
# ==========================================
if __name__ == "__main__":
    from src.ingestion.embedder import get_embedding_model
    from langchain_core.documents import Document
    
    embedder = get_embedding_model()
    
    test_chunks = [
        Document(page_content="LangChain adalah framework untuk membangun aplikasi LLM.", metadata={"source": "test"}),
        Document(page_content="ChromaDB adalah database vektor open-source.", metadata={"source": "test"}),
    ]
    
    test_dir = str(ROOT_DIR / "chroma_db_test")
    vs = get_vector_store(chunks=test_chunks, embedding_model=embedder, persist_directory=test_dir, reset=True)
    print("\n[BERHASIL] Test Vector Store siap digunakan.")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
