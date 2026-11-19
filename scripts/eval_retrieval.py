"""Evaluasi retrieval-only (tanpa memanggil LLM generator).

Metrik:
- Hit@5: apakah chunk yang memuat pasal yang diharapkan ada di 5 konteks.
- MRR: 1/rank konteks pertama yang memuat pasal yang diharapkan.

Jalankan dari root project:

    python scripts/eval_retrieval.py
    python scripts/eval_retrieval.py --limit 6
    python scripts/eval_retrieval.py --no-rerank

Skrip ini memakai Gemini Embedding untuk dense retrieval. Reranker memakai
OpenRouter jika tersedia; jika tidak, kolom "hybrid + rerank" dilewati.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    CHROMA_DB_DIR,
    OPENROUTER_API_KEY,
    RETRIEVAL_FETCH_K,
    RETRIEVAL_FINAL_K,
    RETRIEVAL_RERANK_CANDIDATES,
)
from src.ingestion.embedder import get_embedding_model
from src.retrieval.retriever import (
    LegalHybridRetriever,
    OpenRouterReranker,
    document_key,
    enrich_documents_with_pasal_context,
    extract_pasal_numbers,
    tokenize_indonesian,
)

# Label pasal diverifikasi langsung dari teks PDF (heading pasal).
RETRIEVAL_CASES = [
    {
        "question": "Berapa batas maksimal waktu kerja lembur dalam 1 hari dan 1 minggu menurut PP 35 Tahun 2021?",
        "expected": [26],
    },
    {
        "question": "Apakah pekerja PKWT berhak mendapatkan uang kompensasi saat kontrak berakhir?",
        "expected": [15],
    },
    {
        "question": "Bagaimana perhitungan uang kompensasi PKWT untuk masa kerja 12 bulan terus menerus?",
        "expected": [16],
    },
    {
        "question": "Berapa jangka waktu maksimal PKWT berdasarkan PP 35 Tahun 2021?",
        "expected": [8],
    },
    {
        "question": "Apakah perusahaan alih daya wajib berbentuk badan hukum?",
        "expected": [20],
    },
    {
        "question": "Berapa uang pesangon untuk masa kerja 3 tahun tetapi kurang dari 4 tahun?",
        "expected": [40],
    },
    {
        "question": "Bagaimana cara menghitung upah kerja lembur per jam?",
        "expected": [32],
    },
    {
        "question": "Berapa hari istirahat mingguan untuk pekerja dengan 6 hari kerja dalam seminggu?",
        "expected": [22],
    },
    {
        "question": "Apa hak pekerja jika PHK karena perusahaan melakukan efisiensi karena kerugian?",
        "expected": [43],
    },
    {
        "question": "Apa hak pekerja jika perusahaan melakukan penggabungan atau peleburan dan pekerja tidak bersedia melanjutkan hubungan kerja?",
        "expected": [41],
    },
    {
        "question": "Apakah PKWT boleh mensyaratkan masa percobaan kerja?",
        "expected": [12],
    },
    {
        "question": "Berapa lama waktu kerja dalam 1 hari untuk 5 hari kerja dalam seminggu?",
        "expected": [21],
    },
    {
        "question": "Siapa yang berhak atas uang pesangon jika pekerja meninggal dunia?",
        "expected": [57],
    },
    {
        "question": "Apa kewajiban pengusaha terkait uang penggantian hak cuti tahunan yang belum diambil?",
        "expected": [40],
    },
    {
        "question": "Apa isi Pasal 26 ayat (1) PP 35 Tahun 2021?",
        "expected": [26],
    },
    {
        "question": "Jelaskan Pasal 20 ayat (1) tentang alih daya.",
        "expected": [20],
    },
]


def build_corpus():
    embeddings = get_embedding_model()
    vector_store = Chroma(
        persist_directory=str(CHROMA_DB_DIR),
        embedding_function=embeddings,
    )
    data = vector_store.get()
    documents = [
        Document(page_content=text, metadata=dict(metadata or {}))
        for text, metadata in zip(
            data.get("documents") or [], data.get("metadatas") or []
        )
    ]
    def page_number(doc: Document) -> int:
        try:
            return int(doc.metadata.get("page") or 0)
        except (TypeError, ValueError):
            return 0

    documents.sort(
        key=lambda doc: (str(doc.metadata.get("source", "")), page_number(doc))
    )
    enrich_documents_with_pasal_context(documents)

    references_by_key: Dict[str, Set[int]] = {
        document_key(doc): set(doc.metadata.get("pasal_refs") or [])
        for doc in documents
    }
    return vector_store, documents, references_by_key


def build_bm25(documents: Sequence[Document], k: int) -> BM25Retriever:
    bm25 = BM25Retriever.from_documents(
        list(documents), preprocess_func=tokenize_indonesian
    )
    bm25.k = k
    return bm25


def build_retrievers(vector_store, documents, include_rerank: bool):
    retrievers = {
        "dense-only (k=5)": vector_store.as_retriever(
            search_type="similarity", search_kwargs={"k": RETRIEVAL_FINAL_K}
        ),
        "bm25-only (k=5)": build_bm25(documents, k=RETRIEVAL_FINAL_K),
        "hybrid RRF (no rerank)": LegalHybridRetriever(
            dense_retriever=vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": RETRIEVAL_FETCH_K}
            ),
            bm25_retriever=build_bm25(documents, k=RETRIEVAL_FETCH_K),
            reranker=None,
            all_docs=list(documents),
            final_k=RETRIEVAL_FINAL_K,
            rerank_candidates=RETRIEVAL_RERANK_CANDIDATES,
            enable_query_expansion=False,
        ),
    }

    if include_rerank:
        retrievers["hybrid + rerank"] = LegalHybridRetriever(
            dense_retriever=vector_store.as_retriever(
                search_type="similarity", search_kwargs={"k": RETRIEVAL_FETCH_K}
            ),
            bm25_retriever=build_bm25(documents, k=RETRIEVAL_FETCH_K),
            reranker=OpenRouterReranker(top_n=RETRIEVAL_FINAL_K),
            all_docs=list(documents),
            final_k=RETRIEVAL_FINAL_K,
            rerank_candidates=RETRIEVAL_RERANK_CANDIDATES,
            enable_query_expansion=False,
        )

    return retrievers


def first_hit_rank(
    documents: Sequence[Document],
    expected: Set[int],
    references_by_key: Dict[str, Set[int]],
) -> Optional[int]:
    for rank, document in enumerate(documents, start=1):
        refs = references_by_key.get(document_key(document))
        if refs is None:
            refs = set(extract_pasal_numbers(document.page_content))
        if expected & refs:
            return rank
    return None


def evaluate(retriever, name, cases, references_by_key, sleep_seconds):
    ranks: List[Optional[int]] = []
    latencies: List[float] = []
    misses = []
    reranked_queries = 0

    for case in cases:
        started = time.perf_counter()
        documents = retriever.invoke(case["question"])
        latencies.append(time.perf_counter() - started)
        if any("rerank_score" in doc.metadata for doc in documents):
            reranked_queries += 1

        rank = first_hit_rank(documents, set(case["expected"]), references_by_key)
        ranks.append(rank)
        if rank is None:
            misses.append((case["question"], case["expected"], [
                (
                    doc.metadata.get("page"),
                    doc.metadata.get("pasal_refs"),
                )
                for doc in documents
            ]))

        if sleep_seconds:
            time.sleep(sleep_seconds)

    total = len(ranks)
    hit_at_k = sum(rank is not None for rank in ranks) / total
    mrr = sum(1.0 / rank for rank in ranks if rank is not None) / total
    mean_latency = sum(latencies) / total

    return {
        "name": name,
        "hit@5": hit_at_k,
        "mrr": mrr,
        "latency": mean_latency,
        "reranked_queries": reranked_queries,
        "uses_reranker": reranked_queries > 0,
        "misses": misses,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluasi retrieval KawanKerja AI")
    parser.add_argument("--limit", type=int, help="Batasi jumlah pertanyaan")
    parser.add_argument(
        "--no-rerank",
        action="store_true",
        help="Lewati kolom reranker (tidak butuh OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.4,
        help="Jeda antar pertanyaan untuk menghindari rate limit (default: 0.4s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Tampilkan pertanyaan yang gagal beserta konteks yang didapat",
    )
    args = parser.parse_args()

    cases = RETRIEVAL_CASES[: args.limit] if args.limit else RETRIEVAL_CASES
    include_rerank = not args.no_rerank
    if include_rerank and not (OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")):
        print("OPENROUTER_API_KEY tidak tersedia; kolom reranker dilewati.")
        include_rerank = False

    print(f"Membangun korpus dan retriever untuk {len(cases)} pertanyaan...")
    vector_store, documents, references_by_key = build_corpus()
    print(f"Korpus: {len(documents)} chunk")

    retrievers = build_retrievers(
        vector_store, documents, include_rerank=include_rerank
    )

    results = []
    for name, retriever in retrievers.items():
        print(f"\nMenjalankan: {name}")
        results.append(
            evaluate(
                retriever,
                name,
                cases,
                references_by_key,
                sleep_seconds=args.sleep,
            )
        )

    print("\n" + "=" * 72)
    print(f"{'Retriever':<26} {'Hit@5':>8} {'MRR':>8} {'Latency':>10}")
    print("-" * 72)
    for result in results:
        print(
            f"{result['name']:<26} "
            f"{result['hit@5']:>8.3f} "
            f"{result['mrr']:>8.3f} "
            f"{result['latency']:>9.2f}s"
        )
    print("=" * 72)
    for result in results:
        if not result["name"].startswith("hybrid + rerank"):
            continue
        status = (
            f"berhasil dipakai pada {result['reranked_queries']}/{len(cases)} query"
            if result["uses_reranker"]
            else f"tidak aktif (0/{len(cases)} query berhasil)"
        )
        print(f"{result['name']}: reranker {status}.")

    if args.verbose:
        for result in results:
            if not result["misses"]:
                continue
            print(f"\nMisses untuk {result['name']}:")
            for question, expected, retrieved in result["misses"]:
                print(f"- {question}")
                print(f"  expected pasal: {expected}")
                print(f"  retrieved: {retrieved}")


if __name__ == "__main__":
    main()
