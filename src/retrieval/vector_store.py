import os
from langchain_chroma import Chroma
from src.config import CHROMA_DB_DIR

def get_vector_store(chunks=None, embedding_model=None, persist_directory=None):
    """
    Menyimpan chunks ke dalam ChromaDB atau memuat database jika sudah ada.
    """
    if persist_directory is None:
        persist_directory = str(CHROMA_DB_DIR)

    if embedding_model is None:
        raise ValueError("Model embedding harus disertakan!")

    print(f"Mengakses Vector Store di direktori: {persist_directory}")
    
    # Skenario 1: Jika kita memberikan 'chunks', berarti kita ingin memasukkan data baru
    if chunks:
        print(f"Menyimpan {len(chunks)} chunks ke dalam ChromaDB...")
        vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embedding_model,
            persist_directory=str(persist_directory)
        )
        print("Data berhasil disimpan!")
        
    # Skenario 2: Jika 'chunks' kosong, berarti kita hanya ingin membaca data yang sudah ada
    else:
        if not os.path.exists(persist_directory):
            raise FileNotFoundError("Database belum ada. Masukkan dokumen terlebih dahulu!")
            
        print("Memuat Vector Store yang sudah ada...")
        vector_store = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=embedding_model
        )
        
    return vector_store

# ==========================================
# Blok testing
# ==========================================
if __name__ == "__main__":
    from src.ingestion.embedder import get_embedding_model
    from langchain_core.documents import Document
    
    # 1. Siapkan embedder
    embedder = get_embedding_model()
    
    # 2. Buat chunk palsu untuk testing
    test_chunks = [
        Document(page_content="LangChain adalah framework untuk membangun aplikasi LLM."),
        Document(page_content="ChromaDB adalah database vektor open-source."),
        Document(page_content="Pinecone adalah layanan database vektor berbasis cloud."),
    ]
    
    # 3. Simpan ke database
    vs = get_vector_store(chunks=test_chunks, embedding_model=embedder)
    print("\n[BERHASIL] Vector Store siap digunakan.")
