from langchain_huggingface import HuggingFaceEmbeddings
from src.config import EMBEDDING_MODEL_NAME, get_device

def get_embedding_model(model_name: str = EMBEDDING_MODEL_NAME):
    print(f"Mempersiapkan model embedding: {model_name}")
    
    device = get_device()
    print(f"Hardware yang digunakan untuk embedding: {device.upper()}")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={'device': device},
        encode_kwargs={'normalize_embeddings': True} 
    )
    
    return embeddings


# =======Blok testing=========
if __name__ == "__main__":
    embedder = get_embedding_model()
    
    teks_uji = "Mengubah teks menjadi angka agar dipahami oleh mesin."
    vektor = embedder.embed_query(teks_uji)
    
    print("\n[BERHASIL]")
    print(f"Dimensi vektor (jumlah angka): {len(vektor)}")
    print(f"Cuplikan vektor 5 angka pertama: {vektor[:5]}")
