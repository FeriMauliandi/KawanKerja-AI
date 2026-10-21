import streamlit as st
import os
import sys
import time
import requests

# Konfigurasi UI Streamlit
st.set_page_config(page_title="KawanKerja AI", page_icon="💼", layout="wide")

# Konfigurasi URL Backend FastAPI
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def check_backend_health() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=2)
        return resp.status_code == 200 and resp.json().get("model_loaded", False)
    except Exception:
        return False

# Sidebar Informasi Arsitektur AI
with st.sidebar:
    st.title("💼 KawanKerja AI")
    st.caption("Asisten AI Konsultasi Regulasi Ketenagakerjaan")
    st.markdown("---")
    
    st.markdown("### 🌐 Status Arsitektur Client-Server:")
    backend_online = check_backend_health()
    if backend_online:
        st.success(f"🟢 **Backend Online** (`{BACKEND_URL}`)")
    else:
        st.error(f"🔴 **Backend Offline** (`{BACKEND_URL}`)")
        st.caption("Jalankan FastAPI backend di terminal:")
        st.code("uvicorn backend.api:app --reload", language="bash")
        
    execution_mode = st.radio(
        "Mode Komunikasi:",
        options=["REST API Client (Rekomendasi)", "Embedded Direct (Fallback Lokal)"],
        index=0 if backend_online else 1
    )
    
    st.markdown("---")
    st.markdown("### ⚙️ Spesifikasi Sistem:")
    st.markdown("""
    - **Arsitektur**: Decoupled Client-Server (Streamlit -> FastAPI)
    - **LLM Generator**: `Qwen 3.8 27B` *(via Groq LPU)*
    - **Embedding**: `Qwen/Qwen3-Embedding-0.6B`
    - **Reranker**: `BAAI/bge-reranker-v2-m3`
    - **Metode Pencarian**: Hybrid Search (BM25 + ChromaDB)
    - **Conversational Memory**: Multi-Turn Query Reformulation
    - **Dasar Regulasi**: PP No. 35 Tahun 2021
    """)
    st.markdown("---")
    if st.button("🗑️ Hapus Riwayat Percakapan"):
        st.session_state.messages = []
        st.rerun()

st.title("💼 KawanKerja AI: Asisten Regulasi Ketenagakerjaan Indonesia")
st.markdown(
    "Tempat bertanya dan konsultasi hak kerja karyawan seputar **Kontrak PKWT**, **Uang Kompensasi**, "
    "**Ketentuan Lembur**, dan **Pesangon PHK** berdasarkan **PP No. 35 Tahun 2021**."
)

# Inisialisasi riwayat pesan di session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan riwayat pesan
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("standalone") and message["standalone"] != message.get("original_question"):
            st.caption(f"🔍 _Pertanyaan terkontekstualisasi: {message['standalone']}_")
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("📚 Dokumen & Rujukan Pasal yang Digunakan"):
                for s in message["sources"]:
                    st.markdown(f"**Sumber**: `{s['source']}` (Halaman: **{s['page']}**)")
                    st.caption(f"_{s['snippet']}..._")

def call_rest_api(question: str, history: list):
    payload = {
        "question": question,
        "chat_history": history
    }
    resp = requests.post(f"{BACKEND_URL}/api/chat", json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Backend API Error ({resp.status_code}): {resp.text}")
    return resp.json()

@st.cache_resource
def load_local_chain():
    # Fallback jika user memilih mode Embedded
    root_dir = os.path.abspath(os.path.dirname(__file__))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    from src.generation.chain import create_rag_chain
    return create_rag_chain(return_docs=True)

# Kolom input untuk user
if prompt := st.chat_input("Tulis pertanyaan Anda seputar aturan kerja (contoh: Berapa batas maksimal waktu lembur dalam seminggu?)..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Simpan riwayat chat untuk pengiriman ke backend
    history_before_prompt = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        start_time = time.time()
        with st.spinner("Memproses pertanyaan ke KawanKerja Engine..."):
            try:
                if execution_mode == "REST API Client (Rekomendasi)":
                    result = call_rest_api(prompt, history_before_prompt)
                    backend_label = "FastAPI REST API"
                else:
                    chain = load_local_chain()
                    result = chain.invoke({
                        "question": prompt,
                        "chat_history": history_before_prompt
                    })
                    backend_label = "Direct Embedded"

                latency = time.time() - start_time
                jawaban = result["answer"]
                sources = result.get("sources", [])
                standalone = result.get("standalone_question", prompt)

                if standalone and standalone != prompt:
                    st.caption(f"🔍 _Pertanyaan terkontekstualisasi: {standalone}_")

                st.markdown(jawaban)
                st.caption(f"⏱️ Waktu respons: **{latency:.2f} detik** via `{backend_label}`")

                if sources:
                    with st.expander("📚 Dokumen & Rujukan Pasal yang Digunakan"):
                        for s in sources:
                            st.markdown(f"**Sumber**: `{s['source']}` (Halaman: **{s['page']}**)")
                            st.caption(f"_{s['snippet']}..._")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": jawaban,
                    "sources": sources,
                    "standalone": standalone,
                    "original_question": prompt
                })

            except Exception as e:
                st.error(f"❌ Terjadi kendala saat memproses permintaan: {e}")
                if "Connection refused" in str(e) or "Failed to establish" in str(e):
                    st.info("💡 Pastikan server backend FastAPI sudah aktif dengan perintah: `uvicorn backend.api:app --reload`")
