from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_entrypoints_exist():
    expected_files = [
        "frontend/app.py",
        "scripts/ingest.py",
        "scripts/eval.py",
        "backend/api.py",
        "backend/schemas.py",
        "src/config.py",
        "src/generation/chain.py",
        "src/generation/prompt.py",
        "src/retrieval/retriever.py",
        "src/retrieval/vector_store.py",
        "pyproject.toml",
    ]

    missing = [path for path in expected_files if not (ROOT / path).exists()]

    assert missing == []


def test_prompt_contains_core_rag_guardrails():
    prompt_file = ROOT / "src/generation/prompt.py"
    prompt_text = prompt_file.read_text(encoding="utf-8")

    assert "berdasarkan potongan konteks" in prompt_text.lower()
    assert "jangan mengarang" in prompt_text.lower()
    assert "{context}" in prompt_text
    assert "{question}" in prompt_text
