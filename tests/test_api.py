import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from fastapi.testclient import TestClient
from backend.api import app, ml_models

def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "KawanKerja AI Engine"
    assert data["status"] == "online"

def test_health_check_unloaded():
    ml_models.clear()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["model_loaded"] is False

def test_chat_endpoint_schema_and_response():
    class MockRAGChain:
        def invoke(self, input_data):
            q = input_data.get("question") if isinstance(input_data, dict) else input_data
            return {
                "answer": "Berdasarkan Pasal 8 ayat (1) PP 35/2021, batas maksimal PKWT adalah 5 tahun.",
                "sources": [
                    {
                        "source": "PP_No_35_Tahun_2021.pdf",
                        "page": 6,
                        "snippet": "Pasal 8 (1) PKWT berdasarkan jangka waktu dapat dibuat untuk paling lama 5 tahun."
                    }
                ],
                "standalone_question": q
            }
            
    ml_models["rag_chain"] = MockRAGChain()
    client = TestClient(app)
    
    # Uji kirim query chat
    response = client.post("/api/chat", json={
        "question": "Berapa lama batas maksimal kontrak PKWT?",
        "chat_history": [
            {"role": "user", "content": "Halo"},
            {"role": "assistant", "content": "Halo, ada yang bisa dibantu?"}
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "Pasal 8" in data["answer"]
    assert data["standalone_question"] == "Berapa lama batas maksimal kontrak PKWT?"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source"] == "PP_No_35_Tahun_2021.pdf"
    assert data["sources"][0]["page"] == 6
