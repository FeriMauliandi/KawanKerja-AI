from typing import List, Optional

import pytest
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor
from langchain_core.retrievers import BaseRetriever

from src.retrieval import retriever as retriever_module
from src.retrieval.retriever import (
    LegalHybridRetriever,
    OpenRouterReranker,
    build_citation_snippet,
    clean_pdf_artifacts,
    deduplicate_documents,
    enrich_documents_with_pasal_context,
    extract_pasal_headings,
    extract_pasal_numbers,
    extract_pasal_refs,
    reciprocal_rank_fusion,
    resolve_exact_pasal_documents,
    select_diverse_documents,
    tokenize_indonesian,
)


def make_doc(content: str, page: int = 1, source: str = "PP_No_35_Tahun_2021.pdf"):
    return Document(page_content=content, metadata={"source": source, "page": page})


class StaticRetriever(BaseRetriever):
    documents: List[Document]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        return list(self.documents)


class TruncatingReranker(BaseDocumentCompressor):
    limit: int = 2

    def compress_documents(self, documents, query, callbacks=None):
        return list(documents)[: self.limit]


# ---------------------------------------------------------------------------
# Tokenizer & pasal parsing
# ---------------------------------------------------------------------------
def test_tokenize_indonesian_normalizes_punctuation_and_stopwords():
    tokens = tokenize_indonesian("Berapa Pasal 26 ayat (1) yang dan atau?")
    assert tokens == ["berapa", "pasal", "26", "ayat", "1"]


def test_extract_pasal_refs_supports_ayat_and_multiple_articles():
    assert extract_pasal_refs("Pasal 26 ayat (1)") == [(26, 1)]
    assert extract_pasal_refs("pasal 8 dan Pasal 40 ayat 2") == [(8, None), (40, 2)]
    assert extract_pasal_refs("tidak ada rujukan") == []


def test_clean_pdf_artifacts_removes_page_headers():
    assert (
        clean_pdf_artifacts("2021, No.45 -16- \nPasal 26 (1) lembur 4 jam.")
        == "Pasal 26 (1) lembur 4 jam."
    )
    assert (
        clean_pdf_artifacts("No. 6647 -7- \nPasal 31 Cukup jelas.")
        == "Pasal 31 Cukup jelas."
    )


def test_build_citation_snippet_starts_at_late_pasal_heading():
    text = ("sisa pasal sebelumnya " * 12) + "\nPasal 26\n(1) lembur 4 jam."
    snippet = build_citation_snippet(text, max_chars=80)
    assert snippet.startswith("Pasal 26")
    assert "lembur 4 jam" in snippet


def test_extract_pasal_numbers_from_chunk_text():
    text = "Pasal 15 (1) ... Pasal 16 (1) ... Pasal 15 (2)"
    assert extract_pasal_numbers(text) == [15, 16]


def test_extract_pasal_headings_ignores_cross_references():
    text = (
        "Pasal 26 \n(1) Waktu Kerja Lembur paling lama 4 jam.\n"
        "Pasal 27 \n(1) Ketentuan sebagaimana dimaksud dalam Pasal 21 ayat (2)."
    )
    assert extract_pasal_headings(text) == [26, 27]


def test_extract_pasal_headings_accepts_inline_ayat_marker():
    assert extract_pasal_headings("Pasal 40 (1) pengusaha wajib membayar.") == [40]


# ---------------------------------------------------------------------------
# Fusion & diversity
# ---------------------------------------------------------------------------
def test_deduplicate_documents_uses_content_not_metadata():
    first = make_doc("Pasal 26 (1) lembur 4 jam.", page=15)
    duplicate = make_doc("Pasal 26 (1) lembur 4 jam.", page=16)
    unique = make_doc("Pasal 8 (1) PKWT 5 tahun.", page=6)
    result = deduplicate_documents([first, duplicate, unique])
    assert len(result) == 2
    assert result[0].page_content == first.page_content


def test_reciprocal_rank_fusion_puts_consensus_document_first():
    consensus = make_doc("Pasal 26 (1) lembur 4 jam.", page=15)
    dense_only = make_doc("Pasal 8 (1) PKWT 5 tahun.", page=6)
    bm25_only = make_doc("Pasal 22 istirahat mingguan.", page=14)

    fused = reciprocal_rank_fusion(
        [
            ([dense_only, consensus], 0.55, "dense"),
            ([bm25_only, consensus], 0.45, "bm25"),
        ]
    )

    assert fused[0].page_content == consensus.page_content
    assert fused[0].metadata["retrieval_sources"] == ["bm25", "dense"]
    assert len(fused) == 3


def test_select_diverse_documents_caps_per_page_then_fills_remaining_slots():
    page_one = [make_doc(f"Pasal 40 ayat {i}", page=25) for i in range(4)]
    page_two = make_doc("Pasal 41", page=27)

    selected = select_diverse_documents(
        page_one + [page_two], limit=3, max_per_page=2
    )

    assert len(selected) == 3
    assert [doc.metadata["page"] for doc in selected] == [25, 25, 27]


# ---------------------------------------------------------------------------
# Exact pasal resolver
# ---------------------------------------------------------------------------
def test_exact_pasal_resolver_prefers_requested_ayat():
    ayat_1 = make_doc("Pasal 26 (1) Waktu Kerja Lembur paling lama 4 jam.", page=15)
    ayat_2 = make_doc("Pasal 26 (2) tidak termasuk istirahat mingguan.", page=15)
    unrelated = make_doc("Pasal 8 (1) PKWT paling lama 5 tahun.", page=6)

    result = resolve_exact_pasal_documents(
        "Pasal 26 ayat (1)", [ayat_2, unrelated, ayat_1], limit=2
    )

    assert result
    assert result[0].page_content == ayat_1.page_content


def test_exact_pasal_resolver_returns_empty_without_citation():
    assert (
        resolve_exact_pasal_documents(
            "Bagaimana cara menghitung lembur?", [make_doc("Pasal 26 (1)")]
        )
        == []
    )


def test_enrich_documents_inherits_pasal_for_continuation_chunk():
    heading = make_doc("Pasal 40 (1) pengusaha wajib membayar pesangon.", page=25)
    continuation = make_doc("(2) uang pesangon diberikan dengan ketentuan:", page=26)
    other_source = make_doc("Pasal 8 (1) PKWT lima tahun.", page=2, source="Penjelasan.pdf")

    enrich_documents_with_pasal_context([heading, continuation, other_source])

    assert heading.metadata["pasal_refs"] == [40]
    assert heading.metadata["pasal_explicit"] is True
    assert continuation.metadata["pasal_refs"] == [40]
    assert continuation.metadata["pasal_inherited"] is True
    assert other_source.metadata["pasal_refs"] == [8]


def test_exact_resolver_uses_inherited_pasal_but_ranks_it_lower():
    heading = make_doc("Pasal 40 (1) pengusaha wajib membayar pesangon.", page=25)
    continuation = make_doc("(2) uang pesangon diberikan dengan ketentuan:", page=26)
    enrich_documents_with_pasal_context([heading, continuation])

    result = resolve_exact_pasal_documents(
        "Pasal 40 ayat (1)", [continuation, heading], limit=2
    )

    assert result[0].page_content == heading.page_content
    assert any(doc.page_content == continuation.page_content for doc in result)


def test_exact_pasal_resolver_adds_neighbor_chunks():
    first = make_doc("Pasal 40 (1) pengusaha wajib membayar pesangon.", page=25)
    continuation = make_doc("(2) uang pesangon diberikan dengan ketentuan:", page=25)
    unrelated = make_doc("Pasal 8 (1) PKWT paling lama 5 tahun.", page=6)

    result = resolve_exact_pasal_documents(
        "Pasal 40", [first, continuation, unrelated], limit=3
    )

    assert len(result) == 2
    assert result[0].page_content == first.page_content
    assert result[1].page_content == continuation.page_content


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------
def test_hybrid_retriever_uses_exact_pasal_and_respects_final_k():
    pasal_26 = make_doc("Pasal 26 (1) Waktu Kerja Lembur paling lama 4 jam.", page=15)
    pasal_8 = make_doc("Pasal 8 (1) PKWT paling lama 5 tahun.", page=6)
    unrelated = make_doc("Budidaya lele membutuhkan pH 6.5.", page=1, source="lele.pdf")

    retriever = LegalHybridRetriever(
        dense_retriever=StaticRetriever(documents=[unrelated, pasal_8]),
        bm25_retriever=StaticRetriever(documents=[unrelated]),
        reranker=None,
        all_docs=[pasal_26, pasal_8, unrelated],
        final_k=2,
        rerank_candidates=5,
        enable_query_expansion=False,
    )

    result = retriever.invoke("Apa isi Pasal 26 ayat (1)?")

    assert len(result) == 2
    assert "Pasal 26" in result[0].page_content
    assert "exact_pasal" in result[0].metadata["retrieval_sources"]


def test_hybrid_retriever_applies_reranker_after_fusion():
    docs = [
        make_doc("Pasal 26 (1) lembur 4 jam.", page=15),
        make_doc("Pasal 8 (1) PKWT 5 tahun.", page=6),
        make_doc("Pasal 22 istirahat mingguan.", page=14),
    ]
    retriever = LegalHybridRetriever(
        dense_retriever=StaticRetriever(documents=docs),
        bm25_retriever=None,
        reranker=TruncatingReranker(limit=2),
        all_docs=docs,
        final_k=3,
        rerank_candidates=3,
        enable_query_expansion=False,
    )

    result = retriever.invoke("Apa aturan lembur?")

    assert len(result) == 2


def test_reranker_falls_back_when_api_key_is_missing(monkeypatch):
    monkeypatch.setattr(retriever_module, "OPENROUTER_API_KEY", None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    docs = [make_doc(f"Pasal {number}", page=number) for number in (1, 2, 3)]
    reranker = OpenRouterReranker(top_n=2, api_key=None)

    result = reranker.compress_documents(docs, "Pasal 2")

    assert result == docs[:2]
