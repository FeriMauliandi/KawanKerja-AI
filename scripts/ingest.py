from src.config import DEFAULT_SOURCES, CHUNK_SIZE, CHUNK_OVERLAP
from src.ingestion.loader import load_data
from src.ingestion.chunker import split_documents
from src.ingestion.embedder import get_embedding_model
from src.retrieval.vector_store import get_vector_store

SOURCES = DEFAULT_SOURCES

def run_ingestion_pipeline(sources=None):
    if sources is None:
        sources = DEFAULT_SOURCES

    print("Memulai Data Ingestion Pipeline untuk Regulasi Ketenagakerjaan (PP 35/2021)\n")
    all_chunks = []
    
    for source in sources:
        try:
            raw_docs = load_data(source)
            chunks = split_documents(raw_docs, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
            all_chunks.extend(chunks)
            print(f"Berhasil memproses: {source} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"Gagal memproses {source}: {e}")
            
    if all_chunks:
        print(f"\nMenyiapkan model embedding dan menyimpan {len(all_chunks)} chunks ke ChromaDB.")
        embedder = get_embedding_model()
        get_vector_store(chunks=all_chunks, embedding_model=embedder)
        print("\nSelesai! Semua data regulasi telah masuk ke database dan siap digunakan.")
    else:
        print("\nTidak ada data yang berhasil diproses.")

if __name__ == "__main__":
    run_ingestion_pipeline()
