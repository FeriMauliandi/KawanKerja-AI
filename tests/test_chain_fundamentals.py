import pytest
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda

from src.generation.chain import (
    create_rag_chain,
    normalize_chat_history,
    create_conversational_rag_chain_with_history,
)


class MockLLM(RunnableLambda):
    def __init__(self):
        super().__init__(self._generate)

    def _generate(self, messages):
        # Mengembalikan teks simulasi
        return "Berdasarkan Pasal 8 PP 35/2021, durasi maksimal PKWT adalah 5 tahun."


def test_normalize_chat_history_various_formats():
    raw_history = [
        {"role": "user", "content": "Halo"},
        {"role": "assistant", "content": "Halo! Ada yang bisa dibantu?"},
        ("user", "Pertanyaan lanjutan"),
        ("ai", "Jawaban lanjutan"),
        HumanMessage(content="Pesan ketiga"),
    ]
    normalized = normalize_chat_history(raw_history)
    assert len(normalized) == 5
    assert isinstance(normalized[0], HumanMessage)
    assert isinstance(normalized[1], AIMessage)
    assert isinstance(normalized[2], HumanMessage)
    assert isinstance(normalized[3], AIMessage)
    assert isinstance(normalized[4], HumanMessage)


def test_lcel_rag_chain_synchronous_and_structure():
    mock_llm = MockLLM()
    mock_retriever = RunnableLambda(
        lambda q: [
            Document(
                page_content="Pasal 8 ayat (1) PKWT dibuat paling lama 5 tahun.",
                metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 6}
            )
        ]
    )

    chain = create_rag_chain(return_docs=True, retriever=mock_retriever, llm=mock_llm)

    result = chain.invoke("Berapa lama batas maksimal kontrak PKWT?")
    assert "answer" in result
    assert "sources" in result
    assert "standalone_question" in result
    assert result["standalone_question"] == "Berapa lama batas maksimal kontrak PKWT?"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["page"] == 7  # 6 + 1
    assert "Pasal 8" in result["answer"]


@pytest.mark.asyncio
async def test_lcel_rag_chain_asynchronous():
    mock_llm = MockLLM()
    mock_retriever = RunnableLambda(
        lambda q: [
            Document(
                page_content="Pasal 8 ayat (1) PKWT dibuat paling lama 5 tahun.",
                metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 6}
            )
        ]
    )

    chain = create_rag_chain(return_docs=True, retriever=mock_retriever, llm=mock_llm)

    result = await chain.ainvoke({
        "question": "Bagaimana jika dilakukan perpanjangan?",
        "chat_history": [{"role": "user", "content": "Tanya PKWT"}]
    })

    assert "answer" in result
    assert "sources" in result
    assert "standalone_question" in result


def test_conversational_chain_with_session_history():
    mock_llm = MockLLM()
    mock_retriever = RunnableLambda(
        lambda q: [
            Document(
                page_content="Pasal 8 ayat (1) PKWT dibuat paling lama 5 tahun.",
                metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 6}
            )
        ]
    )

    base_chain = create_rag_chain(return_docs=True, retriever=mock_retriever, llm=mock_llm)
    conv_chain = create_conversational_rag_chain_with_history(chain=base_chain)

    config = {"configurable": {"session_id": "session_user_123"}}
    res1 = conv_chain.invoke({"question": "Pertanyaan 1"}, config=config)
    assert "answer" in res1

    res2 = conv_chain.invoke({"question": "Pertanyaan 2 lanjutan"}, config=config)
    assert "answer" in res2
