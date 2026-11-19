import os
import sys
import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Any, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

# Memastikan Python bisa membaca folder root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.config import LLM_MODEL_NAME
from src.generation.chain import create_rag_chain
from backend.schemas import QueryRequest, SourceItem, QueryResponse

# Dictionary global untuk menyimpan model yang dimuat
ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Memuat KawanKerja RAG Chain (Groq: {LLM_MODEL_NAME}) ke dalam memori...")
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
    description="API Asisten Regulasi Ketenagakerjaan Indonesia (PP No. 35 Tahun 2021) bertenaga Groq GPT-OSS, Gemini Embedding, Hybrid Retrieval (BM25 + Dense + Exact-Pasal + RRF), dan reranker neural opsional",
    version="1.0.0",
    lifespan=lifespan
)

# Aktifkan CORS agar frontend (Streamlit / React / Vue) bisa mengakses API.
# Browser menolak kombinasi origin "*" dengan credentials, jadi credentials
# hanya diaktifkan jika origin dibatasi lewat CORS_ALLOW_ORIGINS.
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static modern web frontend
frontend_dir = os.path.abspath(os.path.join(root_dir, "frontend"))
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend_app")

@app.get("/")
async def root():
    return {
        "service": "KawanKerja AI Engine",
        "status": "online",
        "documentation": "/docs",
        "llm_provider": f"Groq ({LLM_MODEL_NAME})",
        "features": ["LCEL Pipeline", "Hybrid Retrieval (BM25 + Dense + Exact-Pasal + RRF)", "Optional Neural Reranker", "Multi-Turn Conversational Memory"],
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
        chain = ml_models["rag_chain"]
        payload = {
            "question": request.question,
            "chat_history": request.chat_history or []
        }
        
        # Eksekusi non-blocking asinkron via LangChain ainvoke (dengan fallback ke invoke)
        if hasattr(chain, "ainvoke"):
            try:
                result = await chain.ainvoke(payload)
            except (TypeError, NotImplementedError):
                result = chain.invoke(payload)
        else:
            result = chain.invoke(payload)

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

@app.post("/api/chat/stream")
async def chat_stream_with_rag(request: QueryRequest):
    """Kirim jawaban sebagai Server-Sent Events token demi token.

    ``astream()`` pada pipeline LCEL yang memakai beberapa ``assign`` dapat
    mengembalikan state/intermediate output, bukan token generator secara
    konsisten. Karena itu endpoint ini memakai ``astream_events(v2)`` dan
    hanya meneruskan event ``on_chat_model_stream`` dari langkah
    ``GenerateAnswer``.
    """
    if "rag_chain" not in ml_models:
        raise HTTPException(status_code=503, detail="Model RAG belum siap di memori server.")
    
    chain = ml_models["rag_chain"]
    payload = {
        "question": request.question,
        "chat_history": request.chat_history or []
    }

    def sse(event: str, data: dict) -> str:
        """Format satu event SSE dengan JSON yang aman untuk multiline."""
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def chunk_text(chunk) -> str:
        """Ambil teks dari AIMessageChunk/string yang dikirim LangChain."""
        content = getattr(chunk, "content", chunk)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
            return "".join(parts)
        return ""

    async def generate_response():
        answer = []
        final_output = {}
        try:
            # Jalur utama: event model asli, sehingga token diteruskan segera
            # setelah provider LLM menghasilkannya.
            if hasattr(chain, "astream_events"):
                async for event in chain.astream_events(payload, version="v2"):
                    event_name = event.get("event")
                    event_data = event.get("data") or {}
                    metadata = event.get("metadata") or {}

                    if event_name == "on_chat_model_stream":
                        run_name = metadata.get("run_name") or event.get("name", "")
                        if run_name and run_name != "GenerateAnswer":
                            continue
                        text = chunk_text(event_data.get("chunk"))
                        if text:
                            answer.append(text)
                            yield sse("token", {"content": text})
                    elif event_name == "on_chain_end":
                        output = event_data.get("output")
                        if isinstance(output, dict) and "answer" in output:
                            final_output = output

                # Metadata/sources dikirim setelah token terakhir.
                yield sse(
                    "done",
                    {
                        "answer": "".join(answer) or final_output.get("answer", ""),
                        "sources": final_output.get("sources", []),
                        "standalone_question": final_output.get("standalone_question"),
                    },
                )
                return

            # Fallback untuk runnable/mock lama yang belum mendukung events.
            result = await asyncio.to_thread(chain.invoke, payload)
            text = result.get("answer", str(result)) if isinstance(result, dict) else str(result)
            yield sse("token", {"content": text})
            yield sse(
                "done",
                {
                    "answer": text,
                    "sources": result.get("sources", []) if isinstance(result, dict) else [],
                    "standalone_question": result.get("standalone_question") if isinstance(result, dict) else None,
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield sse("error", {"message": "Gagal menghasilkan jawaban.", "detail": str(exc)})

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
