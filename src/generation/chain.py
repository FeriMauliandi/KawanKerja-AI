import os
import sys
from operator import itemgetter
from typing import Union, Dict, Any, List, Optional
from dotenv import load_dotenv

from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableBranch,
    RunnableLambda,
    RunnableConfig,
)
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.documents import Document
from langchain_groq import ChatGroq

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.config import LLM_MODEL_NAME, LLM_TEMPERATURE
from src.retrieval.retriever import get_advanced_retriever
from src.generation.prompt import get_rag_prompt, get_contextualize_prompt

load_dotenv()


def get_groq_llm(model_name: str = LLM_MODEL_NAME, temperature: float = LLM_TEMPERATURE) -> ChatGroq:
    """Menginisialisasi ChatGroq LLM dari environment variable."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY belum disetel di file .env!")
    return ChatGroq(model_name=model_name, temperature=temperature, groq_api_key=groq_api_key)


def normalize_chat_history(history: List[Any]) -> List[BaseMessage]:
    """
    Mengonversi berbagai format riwayat chat (dict, tuple, atau BaseMessage)
    menjadi List[BaseMessage] standar LangChain.
    """
    messages: List[BaseMessage] = []
    for item in history:
        if isinstance(item, BaseMessage):
            messages.append(item)
        elif isinstance(item, dict):
            role = item.get("role", "")
            content = item.get("content", "")
            if role in ("user", "human"):
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                messages.append(AIMessage(content=content))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            role, content = item
            if role in ("user", "human"):
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                messages.append(AIMessage(content=content))
    return messages


def format_docs(docs: List[Document]) -> str:
    """Menggabungkan teks konteks dokumen untuk dimasukkan ke dalam prompt."""
    print("\n" + "="*50)
    print("[DEBUG] DOKUMEN YANG DITARIK RETRIEVER:")
    for i, doc in enumerate(docs):
        sumber = doc.metadata.get('source', 'Sumber tidak diketahui')
        page = doc.metadata.get('page', '-')
        print(f"  [{i+1}] Dari: {sumber} (Hal: {page})")
    print("="*50 + "\n")
    return "\n\n".join(doc.page_content for doc in docs)


def extract_sources(docs: List[Document]) -> List[Dict[str, Any]]:
    """Mengekstraksi metadata sitasi dokumen (sumber, halaman, snippet)."""
    sources = []
    for doc in docs:
        page_val = doc.metadata.get("page")
        if isinstance(page_val, int):
            page_display = page_val + 1
        elif page_val is not None:
            page_display = page_val
        else:
            page_display = "-"

        sources.append({
            "source": os.path.basename(doc.metadata.get("source", "PP_No_35_Tahun_2021.pdf")),
            "page": page_display,
            "snippet": doc.page_content[:250].strip()
        })
    return sources


def create_rag_chain(return_docs: bool = False, retriever=None, llm=None):
    """
    Membangun Conversational RAG Chain deklaratif berbasis LCEL (LangChain Expression Language).
    
    Arsitektur LCEL:
      1. NormalizeInput: Parsing input string/dict & konversi history ke BaseMessage
      2. ReformulateQuery: RunnableBranch untuk kontekstualisasi pertanyaan jika ada history
      3. RetrieveDocuments: Retriever terintegrasi via LCEL pipe (itemgetter -> retriever)
      4. PrepareContext & Sources: Ekstraksi teks konteks dan metadata sitasi
      5. GenerateAnswer: PromptTemplate | ChatGroq | StrOutputParser
      6. FormatOutput: Pemilihan format keluaran sesuai parameter `return_docs`
    
    Mendukung antarmuka Runnable penuh: .invoke(), .ainvoke(), .stream(), .batch(),
    serta otomatis kompatibel dengan LangSmith Tracing & Callbacks.
    """
    if llm is None:
        llm = get_groq_llm()
    if retriever is None:
        retriever = get_advanced_retriever(llm=llm, search_type="similarity", final_k=3, fetch_k=5)

    rag_prompt = get_rag_prompt()
    contextualize_prompt = get_contextualize_prompt()

    # LCEL Sub-chain untuk mereformulasi pertanyaan berdasarkan riwayat
    contextualize_chain = (
        contextualize_prompt
        | llm
        | StrOutputParser()
    ).with_config(run_name="ContextualizeQuestion")

    # Step 1: Normalisasi input ke struktur Dict standar
    def normalize_input(input_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(input_data, str):
            return {
                "question": input_data,
                "chat_history": []
            }
        elif isinstance(input_data, dict):
            raw_history = input_data.get("chat_history", [])
            return {
                "question": input_data.get("question", ""),
                "chat_history": normalize_chat_history(raw_history)
            }
        raise ValueError("Input harus bertipe string atau dict {'question': ..., 'chat_history': ...}")

    # Step 2: Percabangan deklaratif untuk reformulasi pertanyaan
    reformulate_branch = RunnableBranch(
        (lambda x: len(x.get("chat_history", [])) > 0, contextualize_chain),
        (lambda x: x["question"])
    ).with_config(run_name="QueryReformulationBranch")

    # Step 3: Format output akhir
    def format_final_output(data: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        if not return_docs:
            return data["answer"]
        return {
            "answer": data["answer"],
            "sources": data["sources"],
            "standalone_question": data["standalone_question"]
        }

    # Pipeline LCEL Utuh
    rag_chain = (
        RunnableLambda(normalize_input).with_config(run_name="NormalizeInput")
        | RunnablePassthrough.assign(
            standalone_question=reformulate_branch
        )
        | RunnablePassthrough.assign(
            docs=(itemgetter("standalone_question") | retriever).with_config(run_name="RetrieveDocuments")
        )
        | RunnablePassthrough.assign(
            context=lambda x: format_docs(x["docs"]),
            sources=lambda x: extract_sources(x["docs"])
        )
        | RunnablePassthrough.assign(
            answer=(rag_prompt | llm | StrOutputParser()).with_config(run_name="GenerateAnswer")
        )
        | RunnableLambda(format_final_output).with_config(run_name="FormatOutput")
    )

    return rag_chain


# =========================================================================
# LangChain Session Memory Helper (RunnableWithMessageHistory)
# =========================================================================
_session_store: Dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Mengambil atau membuat riwayat percakapan untuk session_id tertentu."""
    if session_id not in _session_store:
        _session_store[session_id] = InMemoryChatMessageHistory()
    return _session_store[session_id]

def create_conversational_rag_chain_with_history(chain=None):
    """
    Membungkus RAG Chain dengan RunnableWithMessageHistory (Pola resmi LangChain Memory).
    Memungkinkan pemanggilan berbasis session_id tanpa perlu mengirim seluruh riwayat manual.
    """
    if chain is None:
        chain = create_rag_chain(return_docs=True)

    return RunnableWithMessageHistory(
        chain,
        get_session_history=get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
        output_messages_key="answer"
    )


# =======Blok testing=========
if __name__ == "__main__":
    chain = create_rag_chain(return_docs=True)

    # Uji Turn 1: Pertanyaan Pertama
    q1 = "Berapa lama batas maksimal kontrak PKWT menurut PP 35 Tahun 2021?"
    print(f"\n[Turn 1] User: {q1}")
    res1 = chain.invoke(q1)
    print("Jawaban Turn 1:\n", res1["answer"])

    # Uji Turn 2: Pertanyaan Follow-up (Menggunakan Conversational Memory)
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": res1["answer"]}
    ]
    q2 = "Bagaimana jika dilakukan perpanjangan?"
    print(f"\n[Turn 2] User: {q2}")
    res2 = chain.invoke({"question": q2, "chat_history": history})
    print(f"\nPertanyaan Standalone Hasil Reformulasi: {res2['standalone_question']}")
    print("Jawaban Turn 2:\n", res2["answer"])
