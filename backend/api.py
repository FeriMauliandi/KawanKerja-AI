import os
import sys
from contextlib import asynccontextmanager
from typing import List, Any, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Memastikan Python bisa membaca folder root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.generation.chain import create_rag_chain
from backend.schemas import QueryRequest, SourceItem, QueryResponse

# Dictionary global untuk menyimpan model yang dimuat
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Memuat KawanKerja RAG Chain (Groq Qwen 3.8 27B) ke dalam memori...")
    try:
        ml_models["rag_chain"] = create_rag_chain(return_docs=True)
        print("Sistem KawanKerja AI siap menerima request!")
    except Exception as e:
        print(f"Gagal memuat RAG: {e}")
    
    yield 
    
    ml_models.clear()
    print("Server dimatikan. Memori dibersihkan.")

# ======fastapi app initialization========
app = FastAPI(
    title="KawanKerja AI Engine",
    description="API Asisten Regulasi Ketenagakerjaan Indonesia (PP No. 35 Tahun 2021) bertenaga Groq & Qwen 3.8 27B",
    version="1.0.0",
    lifespan=lifespan
)

# Aktifkan CORS agar frontend (Streamlit / React / Vue) bisa mengakses API tanpa blokir browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "KawanKerja AI Engine",
        "status": "online",
        "documentation": "/docs",
        "llm_provider": "Groq (qwen/qwen3.8-27b)",
        "features": ["Hybrid Retrieval", "Cross-Encoder Reranker", "Multi-Turn Conversational Memory"],
        "regulation_base": "PP No. 35 Tahun 2021"
    }

@app.get("/health")
async def health_check():
    is_ready = "rag_chain" in ml_models
    return {
        "status": "healthy" if is_ready else "unhealthy",
        "model_loaded": is_ready
    }

@app.post("/api/chat", response_model=QueryResponse)
async def chat_with_rag(request: QueryRequest):
    if "rag_chain" not in ml_models:
        raise HTTPException(status_code=503, detail="Model RAG belum siap di memori server.")
    
    try:
        result = ml_models["rag_chain"].invoke({
            "question": request.question,
            "chat_history": request.chat_history or []
        })
        return QueryResponse(
            answer=result["answer"],
            standalone_question=result.get("standalone_question"),
            sources=[
                SourceItem(
                    source=s["source"],
                    page=s["page"],
                    snippet=s["snippet"]
                )
                for s in result.get("sources", [])
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal: {str(e)}")
