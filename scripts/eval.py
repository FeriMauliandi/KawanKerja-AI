"""Evaluate the RAG pipeline with RAGAS 0.4.3 (legacy metrics API).

Run from the project root:

    python scripts/eval.py
    python scripts/eval.py --limit 2        # smoke test

Catatan versi:
- Metrik diimpor dari `ragas.metrics` (instance siap pakai). Jangan impor dari
  `ragas.metrics.collections`: di sana `faithfulness` dll. adalah MODUL, bukan
  metrik, sehingga evaluate() akan error "All metrics must be initialised
  metric objects".
- LLM (Groq) dan embedding (Gemini) adalah objek LangChain, jadi harus dibungkus
  dengan LangchainLLMWrapper / LangchainEmbeddingsWrapper.
- evaluate() ditandai deprecated di 0.4.x tapi masih berfungsi; versi dipin di
  requirements.txt (ragas==0.4.3).
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv
from langchain_groq import ChatGroq


def _install_ragas_compatibility():
    """Expose the legacy Vertex AI import expected by RAGAS 0.4.3.

    Recent langchain-community releases removed this re-export, while RAGAS
    0.4.3 still imports it at module initialization.
    """
    import importlib
    import types

    try:
        importlib.import_module("langchain_community.chat_models.vertexai")
        return
    except ModuleNotFoundError:
        from langchain_google_vertexai import ChatVertexAI

        legacy_module = types.ModuleType("langchain_community.chat_models.vertexai")
        legacy_module.ChatVertexAI = ChatVertexAI
        sys.modules[legacy_module.__name__] = legacy_module


# Allow `python scripts/eval.py` as documented, in addition to
# `python -m scripts.eval`.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import LLM_MODEL_NAME
from src.ingestion.embedder import get_embedding_model
from src.generation.chain import create_rag_chain

load_dotenv()

# `in_scope=False` = pertanyaan di luar dokumen. Pertanyaan seperti ini TIDAK
# dimasukkan ke metrik RAGAS (context recall/precision tidak bermakna untuk
# ground truth "tidak ada di dokumen"); dicek terpisah sebagai tes penolakan.
EVALUATION_QUESTIONS = [
    {
        "question": "Berapa lama batas maksimal waktu kerja lembur dalam 1 hari dan 1 minggu menurut PP 35 Tahun 2021?",
        "ground_truth": "Berdasarkan Pasal 26 ayat (1) PP 35/2021, waktu kerja lembur hanya dapat dilakukan paling banyak 4 jam dalam 1 hari dan 18 jam dalam 1 minggu, tidak termasuk kerja lembur pada waktu istirahat mingguan atau hari libur resmi.",
        "in_scope": True,
    },
    {
        "question": "Apakah pekerja dengan Perjanjian Kerja Waktu Tertentu (PKWT) berhak mendapatkan uang kompensasi saat kontrak berakhir?",
        "ground_truth": "Ya, pengusaha wajib memberikan uang kompensasi kepada pekerja PKWT yang memiliki masa kerja minimal 1 bulan secara terus-menerus saat berakhirnya jangka waktu PKWT sesuai ketentuan Pasal 15 ayat (1) dan ayat (2) PP 35/2021.",
        "in_scope": True,
    },
    {
        "question": "Bagaimana perhitungan uang kompensasi untuk pekerja PKWT yang telah bekerja selama 12 bulan terus menerus?",
        "ground_truth": "Berdasarkan Pasal 16 ayat (1) huruf a PP 35/2021, pekerja PKWT yang mempunyai masa kerja selama 12 bulan secara terus-menerus diberikan uang kompensasi sebesar 1 bulan upah.",
        "in_scope": True,
    },
    {
        "question": "Berapa batas jangka waktu maksimal keseluruhan kontrak PKWT berdasarkan PP 35 Tahun 2021?",
        "ground_truth": "Berdasarkan Pasal 8 ayat (1) PP 35/2021, PKWT berdasarkan jangka waktu dapat dibuat paling lama 5 tahun, dan jika dilakukan perpanjangan maka total keseluruhan jangka waktu beserta perpanjangannya tidak boleh melebihi 5 tahun.",
        "in_scope": True,
    },
    {
        "question": "Apakah perusahaan alih daya (outsourcing) wajib berbadan hukum perseroan terbatas?",
        # Teks resmi Pasal 20 ayat (1) hanya mensyaratkan "berbentuk badan
        # hukum", tidak spesifik perseroan terbatas.
        "ground_truth": "Tidak harus perseroan terbatas. Berdasarkan Pasal 20 ayat (1) PP 35/2021, Perusahaan Alih Daya harus berbentuk badan hukum dan wajib memenuhi perizinan berusaha yang diterbitkan oleh Pemerintah Pusat; ketentuan tersebut tidak menyebut secara khusus perseroan terbatas.",
        "in_scope": True,
    },
    {
        "question": "Berapa besaran uang pesangon untuk pekerja dengan masa kerja 3 tahun tetapi kurang dari 4 tahun jika terjadi PHK?",
        "ground_truth": "Berdasarkan Pasal 40 ayat (2) huruf d PP 35/2021, pekerja dengan masa kerja 3 tahun atau lebih tetapi kurang dari 4 tahun berhak atas uang pesangon sebesar 4 bulan upah.",
        "in_scope": True,
    },
    {
        "question": "Berapa takaran pakan harian untuk budidaya pembesaran ikan lele?",
        "ground_truth": "Informasi mengenai takaran pakan ikan lele tidak terdapat dalam dokumen regulasi ketenagakerjaan PP No. 35 Tahun 2021.",
        "in_scope": False,
    },
]


def build_evaluation_dataset(limit=None):
    print("Menyiapkan Advanced RAG Pipeline untuk evaluasi...")
    chain = create_rag_chain(return_docs=True)

    questions = EVALUATION_QUESTIONS[:limit] if limit else EVALUATION_QUESTIONS
    print(f"Menjalankan {len(questions)} pertanyaan evaluasi...")

    scored = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    out_of_scope = []  # (question, answer) untuk dicek manual

    for idx, item in enumerate(questions, start=1):
        q, gt = item["question"], item["ground_truth"]
        print(f"  [{idx}/{len(questions)}] Pertanyaan: {q[:60]}...")

        result = chain.invoke(q)
        answer = result["answer"]
        # `contexts` = chunk lengkap yang dipakai prompt generasi.
        contexts = result.get("contexts", [])

        if item.get("in_scope", True):
            scored["question"].append(q)
            scored["answer"].append(answer)
            scored["contexts"].append(contexts)
            scored["ground_truth"].append(gt)
        else:
            out_of_scope.append((q, answer))

    return Dataset.from_dict(scored), out_of_scope


def run_evaluation(output_path="eval_report.csv", limit=None):
    print("Memulai Evaluasi RAGAS untuk KawanKerja AI...")
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY belum disetel. Isi .env atau environment variable terlebih dahulu.")
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise RuntimeError("GOOGLE_API_KEY/GEMINI_API_KEY belum disetel untuk embedding.")

    _install_ragas_compatibility()
    try:
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import (  # instance metrik (BUKAN dari .collections)
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
        from ragas.run_config import RunConfig
    except ImportError as exc:
        raise RuntimeError(f"RAGAS tidak dapat diimpor: {exc}") from exc

    dataset, out_of_scope = build_evaluation_dataset(limit=limit)

    juri_llm = LangchainLLMWrapper(
        ChatGroq(
            model_name=LLM_MODEL_NAME,
            temperature=0.0,
            max_tokens=2048,
            max_retries=3,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )
    )
    juri_embedder = LangchainEmbeddingsWrapper(get_embedding_model())

    # Groq tidak mendukung n>1; answer_relevancy default membuat 3 pertanyaan
    # sekaligus (strictness=3), jadi turunkan ke 1.
    answer_relevancy.strictness = 1

    print("\nMemulai penilaian otomatis metrik RAGAS:")
    print("- Faithfulness (Anti-Halusinasi)")
    print("- Answer Relevancy")
    print("- Context Precision (Relevansi Retriever)")
    print("- Context Recall (Kelengkapan Konteks)")

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=juri_llm,
        embeddings=juri_embedder,
        # Batasi paralelisme agar tidak kena rate limit Groq.
        run_config=RunConfig(timeout=180, max_workers=2, max_retries=5),
        raise_exceptions=False,
    )

    print("\n" + "=" * 50)
    print("HASIL EVALUASI RAGAS (Skor 0.0 - 1.0)")
    print("=" * 50)

    df_hasil = result.to_pandas()
    for col, label in [
        ("faithfulness", "Faithfulness      "),
        ("answer_relevancy", "Answer Relevancy  "),
        ("context_precision", "Context Precision "),
        ("context_recall", "Context Recall    "),
    ]:
        if col in df_hasil:
            n_nan = int(df_hasil[col].isna().sum())
            note = f"  ({n_nan} NaN diabaikan)" if n_nan else ""
            print(f"{label}: {df_hasil[col].mean():.4f}{note}")

    if out_of_scope:
        print("\nTes penolakan (di luar dokumen) -- cek manual, harus menolak/menyatakan tidak ada info:")
        for q, a in out_of_scope:
            print(f"- Q: {q}\n  A: {a[:300]}")

    output_csv = Path(output_path)
    df_hasil.to_csv(output_csv, index=False)
    print(f"\nLaporan lengkap per pertanyaan disimpan ke '{output_csv}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluasi RAG KawanKerja dengan RAGAS")
    parser.add_argument("--output", default="eval_report.csv", help="Path file laporan CSV")
    parser.add_argument("--limit", type=int, help="Batasi jumlah pertanyaan untuk smoke test")
    args = parser.parse_args()
    run_evaluation(output_path=args.output, limit=args.limit)