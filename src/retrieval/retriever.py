from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever, MultiQueryRetriever
from langchain_core.documents import Document

from src.config import CHROMA_DB_DIR, RERANKER_MODEL_NAME, get_reranker_device
from src.ingestion.embedder import get_embedding_model


def get_advanced_retriever(llm, search_type="similarity", final_k=3, fetch_k=5, persist_directory=None):
    print("Menyiapkan Advanced Retriever (MultiQuery + Hybrid + Reranker)...")
    
    if persist_directory is None:
        persist_directory = str(CHROMA_DB_DIR)

    reranker_device = get_reranker_device()
    print(f"Hardware untuk Cross-Encoder Reranker: {reranker_device.upper()}")
    
    embeddings = get_embedding_model()
    vector_store = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    
    db_data = vector_store.get()
    num_docs = len(db_data.get('documents', [])) if db_data else 0
    
    if num_docs == 0:
        safe_fetch_k = 1
        safe_final_k = 1
    else:
        safe_fetch_k = min(fetch_k, num_docs) 
        safe_final_k = min(final_k, num_docs)

    vector_retriever = vector_store.as_retriever(
        search_type=search_type,
        search_kwargs={"k": safe_fetch_k},
    )
    
    if num_docs == 0:
        base_retriever = vector_retriever
    else:
        docs = [Document(page_content=txt, metadata=meta or {}) for txt, meta in zip(db_data['documents'], db_data.get('metadatas', []))]
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = safe_fetch_k
        base_retriever = EnsembleRetriever(retrievers=[bm25_retriever, vector_retriever], weights=[0.5, 0.5])
    
    if llm is None:
        print("LLM tidak diberikan. MultiQueryRetriever dilewati.")
        multi_query_retriever = base_retriever
    else:
        multi_query_retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=llm)
    
    cross_encoder = HuggingFaceCrossEncoder(model_name=RERANKER_MODEL_NAME, model_kwargs={"device": reranker_device})
    compressor = CrossEncoderReranker(model=cross_encoder, top_n=safe_final_k)
    
    final_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=multi_query_retriever
    )
    return final_retriever
