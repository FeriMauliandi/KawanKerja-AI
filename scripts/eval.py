import os
import pandas as pd
from datasets import Dataset
from langchain_groq import ChatGroq

from src.config import LLM_MODEL_NAME
from src.ingestion.embedder import get_embedding_model
from src.generation.chain import create_rag_chain

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

EVALUATION_QUESTIONS = [
    {
        "question": "Berapa lama batas maksimal waktu kerja lembur dalam 1 hari dan 1 minggu menurut PP 35 Tahun 2021?",
        "ground_truth": "Berdasarkan Pasal 26 ayat (1) PP 35/2021, waktu kerja lembur hanya dapat dilakukan paling banyak 4 jam dalam 1 hari dan 18 jam dalam 1 minggu, tidak termasuk kerja lembur pada waktu istirahat mingguan atau hari libur resmi."
    },
    {
        "question": "Apakah pekerja dengan Perjanjian Kerja Waktu Tertentu (PKWT) berhak mendapatkan uang kompensasi saat kontrak berakhir?",
        "ground_truth": "Ya, pengusaha wajib memberikan uang kompensasi kepada pekerja PKWT yang memiliki masa kerja minimal 1 bulan secara terus-menerus saat berakhirnya jangka waktu PKWT sesuai ketentuan Pasal 15 ayat (1) dan ayat (2) PP 35/2021."
    },
    {
        "question": "Bagaimana perhitungan uang kompensasi untuk pekerja PKWT yang telah bekerja selama 12 bulan terus menerus?",
        "ground_truth": "Berdasarkan Pasal 16 ayat (1) huruf a PP 35/2021, pekerja PKWT yang mempunyai masa kerja selama 12 bulan secara terus-menerus diberikan uang kompensasi sebesar 1 bulan upah."
    },
    {
        "question": "Berapa batas jangka waktu maksimal keseluruhan kontrak PKWT berdasarkan PP 35 Tahun 2021?",
        "ground_truth": "Berdasarkan Pasal 8 ayat (1) PP 35/2021, PKWT berdasarkan jangka waktu dapat dibuat paling lama 5 tahun, dan jika dilakukan perpanjangan maka total keseluruhan jangka waktu beserta perpanjangannya tidak boleh melebihi 5 tahun."
    },
    {
        "question": "Apakah perusahaan alih daya (outsourcing) wajib berbadan hukum perseroan terbatas?",
        "ground_truth": "Ya, berdasarkan Pasal 19 PP 35/2021, perusahaan alih daya harus berbentuk badan hukum perseroan terbatas dan wajib memenuhi perizinan berusaha yang diterbitkan oleh pemerintah pusat."
    },
    {
        "question": "Berapa besaran uang pesangon untuk pekerja dengan masa kerja 3 tahun tetapi kurang dari 4 tahun jika terjadi PHK?",
        "ground_truth": "Berdasarkan Pasal 40 ayat (2) huruf d PP 35/2021, pekerja dengan masa kerja 3 tahun atau lebih tetapi kurang dari 4 tahun berhak atas uang pesangon sebesar 4 bulan upah."
    },
    {
        "question": "Berapa pesangon dan UPMK bagi pekerja yang di-PHK karena perusahaan melakukan efisiensi akibat kerugian?",
        "ground_truth": "Berdasarkan Pasal 43 ayat (2) PP 35/2021, pekerja berhak atas uang pesangon sebesar 0,5 kali ketentuan Pasal 40 ayat (2), UPMK sebesar 1 kali ketentuan Pasal 40 ayat (3), dan UPH sesuai Pasal 40 ayat (4)."
    },
    {
        "question": "Berapa takaran pakan harian untuk budidaya pembesaran ikan lele?",
        "ground_truth": "Informasi mengenai takaran pakan ikan lele tidak terdapat dalam dokumen regulasi ketenagakerjaan PP No. 35 Tahun 2021."
    }
]

def build_evaluation_dataset():
    print("Menyiapkan Advanced RAG Pipeline (Groq Qwen 3.8 27B) untuk evaluasi...")
    chain = create_rag_chain(return_docs=True)
    
    data = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": []
    }

    print(f"Menjalankan simulasi {len(EVALUATION_QUESTIONS)} pertanyaan evaluasi...")
    for idx, item in enumerate(EVALUATION_QUESTIONS, start=1):
        q = item["question"]
        gt = item["ground_truth"]
        print(f"  [{idx}/{len(EVALUATION_QUESTIONS)}] Pertanyaan: {q[:60]}...")
        
        result = chain.invoke(q)
        answer = result["answer"]
        contexts = [s["snippet"] for s in result.get("sources", [])]
        
        data["question"].append(q)
        data["answer"].append(answer)
        data["contexts"].append(contexts)
        data["ground_truth"].append(gt)

    return Dataset.from_dict(data)

def run_evaluation():
    print("Memulai Evaluasi RAGAS untuk KawanKerja AI...")
    dataset = build_evaluation_dataset()
    
    groq_api_key = os.getenv("GROQ_API_KEY")
    juri_llm = ChatGroq(model_name=LLM_MODEL_NAME, temperature=0.0, groq_api_key=groq_api_key)
    juri_embedder = get_embedding_model()

    print("\nMemulai penilaian otomatis metrik RAGAS:")
    print("- Faithfulness (Anti-Halusinasi)")
    print("- Answer Relevancy")
    print("- Context Precision (Relevansi Retriever)")
    print("- Context Recall (Kelengkapan Konteks)")
    
    result = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=juri_llm,
        embeddings=juri_embedder
    )
    
    print("\n" + "="*50)
    print("HASIL EVALUASI RAGAS (Skor 0.0 - 1.0)")
    print("="*50)
    
    df_hasil = result.to_pandas()
    print(f"Faithfulness       : {df_hasil['faithfulness'].mean():.4f}")
    print(f"Answer Relevancy   : {df_hasil['answer_relevancy'].mean():.4f}")
    print(f"Context Precision  : {df_hasil['context_precision'].mean():.4f}")
    print(f"Context Recall     : {df_hasil['context_recall'].mean():.4f}")
    
    output_csv = "eval_report.csv"
    df_hasil.to_csv(output_csv, index=False)
    print(f"\nLaporan lengkap per pertanyaan disimpan ke '{output_csv}'")

if __name__ == "__main__":
    run_evaluation()
