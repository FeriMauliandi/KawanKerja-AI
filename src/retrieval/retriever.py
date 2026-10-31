import os
import sys
from pathlib import Path
from typing import Sequence, Optional, List
import requests
from pydantic import Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor
from langchain_core.callbacks import Callbacks
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever, MultiQueryRetriever

from src.config import (
    CHROMA_DB_DIR,
    RERANKER_MODEL_NAME,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
)
from src.ingestion.embedder import get_embedding_model


class OpenRouterNemotronReranker(BaseDocumentCompressor):
    """
    Document Compressor yang memanfaatkan NVIDIA Nemotron 3.5 Rerank 8B
    melalui OpenRouter Rerank API (/api/v1/rerank).
    Menghilangkan overhead loading PyTorch Cross-Encoder lokal sehingga inferensi instan.
    """
    model: str = Field(default=RERANKER_MODEL_NAME)
    top_n: int = Field(default=3)
    api_key: Optional[str] = Field(default=None)
    endpoint: str = Field(default=f"{OPENROUTER_BASE_URL.rstrip('/')}/rerank")
    timeout: int = Field(default=25)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        if not documents:
            return []

        doc_list = list(documents)
        effective_k = min(self.top_n, len(doc_list))
        api_key = self.api_key or OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            print("[PERINGATAN] OPENROUTER_API_KEY belum disetel di .env. Mengembalikan dokumen awal tanpa re-ranking.")
            return doc_list[:effective_k]

        # Prioritaskan model terkonfigurasi, dengan fallback model slug OpenRouter
        candidate_models = [self.model]
        if not self.model.endswith(":free"):
            candidate_models.append(f"{self.model}:free")
        elif self.model.endswith(":free"):
            candidate_models.append(self.model.replace(":free", ""))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kawankerja-ai",
            "X-Title": "KawanKerja AI Nemotron Reranker",
        }

        doc_texts = [doc.page_content for doc in doc_list]

        for target_model in candidate_models:
            payload = {
                "model": target_model,
                "query": query,
                "documents": doc_texts,
                "top_n": effective_k,
            }

            try:
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    ranked_docs: List[Document] = []

                    for item in results:
                        idx = item.get("index")
                        if idx is not None and 0 <= idx < len(doc_list):
                            source_doc = doc_list[idx]
                            # Buat salinan dokumen dengan metadata relevansi Nemotron
                            new_metadata = dict(source_doc.metadata or {})
                            new_metadata["rerank_score"] = float(item.get("relevance_score", 0.0))
                            new_metadata["reranker_model"] = target_model
                            ranked_docs.append(
                                Document(
                                    page_content=source_doc.page_content,
                                    metadata=new_metadata
                                )
                            )

                    if ranked_docs:
                        return ranked_docs[:effective_k]
                else:
                    print(
                        f"[PERINGATAN] OpenRouter Rerank ({target_model}) "
                        f"HTTP {response.status_code}: {response.text}"
                    )
            except Exception as e:
                print(f"[PERINGATAN] Gagal menghubungi endpoint OpenRouter Reranker ({target_model}): {e}")

        # Fallback aman jika API eksternal gagal atau limit tercapai
        print("[FALLBACK] Menggunakan urutan retriever hibrida langsung.")
        return doc_list[:effective_k]


def get_advanced_retriever(llm, search_type="similarity", final_k=3, fetch_k=5, persist_directory=None):
    """
    Membangun arsitektur retrieval tingkat lanjut:
    1. Multi-Query Expansion via Groq LLM
    2. Hybrid Search (Ensemble BM25 Kata Kunci + ChromaDB Vektor Semantik Gemini)
    3. Neural Re-ranking via NVIDIA Nemotron 3.5 Rerank 8B (OpenRouter API)
    """
    print("Menyiapkan Advanced Retriever (Gemini Hybrid + Nemotron 3.5 Reranker)...")
    
    if persist_directory is None:
        persist_directory = str(CHROMA_DB_DIR)

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
        docs = [
            Document(page_content=txt, metadata=meta or {})
            for txt, meta in zip(db_data['documents'], db_data.get('metadatas', []))
        ]
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = safe_fetch_k
        base_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[0.5, 0.5]
        )
    
    if llm is None:
        print("LLM tidak diberikan. MultiQueryRetriever dilewati.")
        multi_query_retriever = base_retriever
    else:
        multi_query_retriever = MultiQueryRetriever.from_llm(retriever=base_retriever, llm=llm)
    
    compressor = OpenRouterNemotronReranker(
        model=RERANKER_MODEL_NAME,
        top_n=safe_final_k
    )
    
    final_retriever = ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=multi_query_retriever
    )
    return final_retriever


# =======Blok testing=========
if __name__ == "__main__":
    test_docs = [
        Document(
            page_content="Pasal 26 PP 35/2021: Waktu lembur paling banyak 4 jam dalam 1 hari dan 18 jam seminggu.",
            metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 14}
        ),
        Document(
            page_content="Budidaya lele dumbo membutuhkan pH air optimal 6.5 sampai 8.",
            metadata={"source": "Perikanan.pdf", "page": 1}
        ),
        Document(
            page_content="Pasal 27 PP 35/2021: Upah kerja lembur wajib dibayarkan oleh pengusaha.",
            metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 15}
        ),
    ]

    reranker = OpenRouterNemotronReranker(top_n=2)
    hasil = reranker.compress_documents(test_docs, "Berapa jam batas maksimal kerja lembur?")
    
    print("\n[HASIL UJI RERANKER]")
    for i, doc in enumerate(hasil, 1):
        print(f"{i}. [Skor: {doc.metadata.get('rerank_score')}] {doc.page_content}")
