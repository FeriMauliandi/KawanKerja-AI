import sys
import os
from typing import Union, Dict, Any, List
from dotenv import load_dotenv
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_groq import ChatGroq

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.config import LLM_MODEL_NAME, LLM_TEMPERATURE
from src.ingestion.embedder import get_embedding_model
from src.retrieval.vector_store import get_vector_store
from src.retrieval.retriever import get_advanced_retriever
from src.generation.prompt import get_rag_prompt, get_contextualize_prompt

load_dotenv()

def get_groq_llm(model_name: str = LLM_MODEL_NAME, temperature: float = LLM_TEMPERATURE):
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY belum disetel di file .env!")
    return ChatGroq(model_name=model_name, temperature=temperature, groq_api_key=groq_api_key)

def normalize_chat_history(history: List[Any]) -> List[BaseMessage]:
    """
    Mengonversi berbagai format riwayat chat (dict, tuple, atau BaseMessage)
    menjadi List[BaseMessage] standar LangChain.
    """
    messages = []
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

def create_rag_chain(return_docs: bool = False):
    """
    Membangun Conversational RAG Chain yang mendukung Multi-turn memory
    dengan integrasi Query Reformulation (History-Aware Retriever).
    """
    llm = get_groq_llm()
    retriever = get_advanced_retriever(llm=llm, search_type="similarity", final_k=3, fetch_k=5)
    
    rag_prompt = get_rag_prompt()
    contextualize_prompt = get_contextualize_prompt()
    contextualize_chain = contextualize_prompt | llm | StrOutputParser()

    def format_docs(docs):
        print("\n" + "="*50)
        print("[DEBUG] DOKUMEN YANG DITARIK RETRIEVER:")
        for i, doc in enumerate(docs):
            sumber = doc.metadata.get('source', 'Sumber tidak diketahui')
            page = doc.metadata.get('page', '-')
            print(f"  [{i+1}] Dari: {sumber} (Hal: {page})")
        print("="*50 + "\n")
        return "\n\n".join(doc.page_content for doc in docs)

    def process_query(input_data: Union[str, Dict[str, Any]]):
        # 1. Parsing input (bisa string tunggal atau dict dengan riwayat chat)
        if isinstance(input_data, str):
            question = input_data
            chat_history = []
        elif isinstance(input_data, dict):
            question = input_data.get("question", "")
            raw_history = input_data.get("chat_history", [])
            chat_history = normalize_chat_history(raw_history)
        else:
            raise ValueError("Input harus bertipe string atau dict {'question': ..., 'chat_history': ...}")

        # 2. Contextual Query Reformulation (Jika ada riwayat chat sebelumnya)
        if chat_history:
            print(f"[REFORMULASI] Mengontekstualisasikan pertanyaan lanjutan: '{question}'...")
            standalone_question = contextualize_chain.invoke({
                "chat_history": chat_history,
                "question": question
            }).strip()
            print(f"[STANDALONE] Pertanyaan Standalone: '{standalone_question}'")
        else:
            standalone_question = question

        # 3. Retrieval dokumen relevan
        docs = retriever.invoke(standalone_question)
        formatted_context = format_docs(docs)

        # 4. Generate jawaban dari LLM
        prompt_messages = rag_prompt.format_messages(
            context=formatted_context,
            chat_history=chat_history,
            question=question
        )
        answer = llm.invoke(prompt_messages).content

        # 5. Format sitasi dokumen
        sources = [
            {
                "source": os.path.basename(doc.metadata.get("source", "PP_No_35_Tahun_2021.pdf")),
                "page": (doc.metadata.get("page", 0) + 1) if isinstance(doc.metadata.get("page"), int) else doc.metadata.get("page", "-"),
                "snippet": doc.page_content[:250].strip()
            }
            for doc in docs
        ]

        if not return_docs:
            return answer
        return {
            "answer": answer,
            "sources": sources,
            "standalone_question": standalone_question
        }

    return RunnableLambda(process_query)

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
