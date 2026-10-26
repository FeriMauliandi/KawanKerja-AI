from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        description="Pertanyaan hukum atau regulasi ketenagakerjaan",
        examples=["Bagaimana jika dilakukan perpanjangan?"]
    )
    chat_history: Optional[List[Dict[str, str]]] = Field(
        default=[],
        description="Riwayat percakapan sebelumnya untuk multi-turn context",
        examples=[
            [
                {"role": "user", "content": "Berapa lama batas maksimal kontrak PKWT menurut PP 35 Tahun 2021?"},
                {"role": "assistant", "content": "Berdasarkan Pasal 8 ayat (1) PP 35/2021, jangka waktu maksimal PKWT adalah 5 tahun."}
            ]
        ]
    )


class SourceItem(BaseModel):
    source: str = Field(..., description="Nama file regulasi sumber")
    page: Any = Field(..., description="Nomor halaman dokumen")
    snippet: str = Field(..., description="Cuplikan teks regulasi terkait")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="Jawaban hasil penalaran RAG LLM")
    standalone_question: Optional[str] = Field(None, description="Pertanyaan yang telah direformulasi berdasarkan riwayat chat")
    sources: List[SourceItem] = Field(default=[], description="Daftar pasal/dokumen rujukan yang digunakan")
