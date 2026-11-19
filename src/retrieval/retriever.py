"""Hybrid retrieval yang disesuaikan dengan ukuran korpus proyek ini.

Korpus saat ini hanya dua PDF (~101 chunk, 68 pasal unik). Pada skala tersebut,
strategi "banyak retriever + MultiQuery di setiap query" justru menambah
latensi dan noise. Strategi yang dipakai di sini:

1. Query analysis: deteksi rujukan pasal/ayat secara eksplisit.
2. Candidate generation: BM25 (k=25) + dense Chroma (k=25).
3. Exact-pasal resolver: scan seluruh korpus (murah karena hanya ~101 chunk)
   untuk memastikan "Pasal 26 ayat (1)" tidak kalah oleh kemiripan semantik.
4. Reciprocal Rank Fusion (RRF): menyatukan BM25 dan dense tanpa perlu
   menormalkan skor cosine vs BM25 yang skalanya berbeda.
5. Deduplikasi + rerank 20 kandidat teratas (opsional; default mati pada
   korpus 101 chunk karena menambah ~4 detik tanpa kenaikan MRR).
6. Diversifikasi: maksimal 2 chunk per halaman, lalu ambil 5 konteks.

Query expansion hanya dijalankan untuk pertanyaan pendek yang tidak mengandung
istilah hukum, dan secara default dimatikan.
"""

import hashlib
import logging
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from pydantic import Field

from langchain_core.callbacks import CallbackManagerForRetrieverRun, Callbacks
from langchain_core.documents import Document
from langchain_core.documents.compressor import BaseDocumentCompressor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.config import (
    CHROMA_DB_DIR,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    RERANKER_MODEL_NAME,
    RERANKER_TIMEOUT,
    RETRIEVAL_BM25_WEIGHT,
    RETRIEVAL_DENSE_WEIGHT,
    RETRIEVAL_ENABLE_QUERY_EXPANSION,
    RETRIEVAL_ENABLE_RERANKER,
    RETRIEVAL_EXACT_PASAL_LIMIT,
    RETRIEVAL_EXACT_PASAL_WEIGHT,
    RETRIEVAL_FETCH_K,
    RETRIEVAL_FINAL_K,
    RETRIEVAL_MAX_PER_PAGE,
    RETRIEVAL_RERANK_CANDIDATES,
)
from src.ingestion.embedder import get_embedding_model

logger = logging.getLogger(__name__)

PASAL_REF_RE = re.compile(
    r"\bpasal\s+(\d+)(?:\s+ayat\s*\(?\s*(\d+)\s*\)?)?", re.IGNORECASE
)
WORD_RE = re.compile(r"[a-z0-9]+")
PDF_PAGE_HEADER_RE = re.compile(
    r"(?m)^\s*(?:20\d{2},\s*No\.?\s*\d+|No\.?\s*\d+)\s*-\s*\d+\s*-\s*"
)
# Judul pasal, bukan rujukan di tengah kalimat. PDF menulis "Pasal 26 \n(1)"
# atau kadang "Pasal 26 (1)", sedangkan rujukan seperti "... ketentuan Pasal
# 40 ayat (4)" tidak diawali baris baru.
PASAL_HEADING_RE = re.compile(
    r"(?m)^[ \t]*pasal[ \t]+(\d+)[ \t]*(?=$|\(|\r?\n)", re.IGNORECASE
)

# Hanya kata fungsi yang dibuang. Kata bermakna hukum seperti "tidak",
# "bukan", "wajib", "dapat", dan "hak" sengaja dipertahankan.
INDONESIAN_STOPWORDS = frozenset(
    {
        "yang", "dan", "atau", "dengan", "untuk", "pada", "dalam", "dari",
        "ini", "itu", "adalah", "sebagai", "oleh", "ke", "di", "se", "secara",
        "akan", "juga", "telah", "sudah", "agar", "bahwa", "jika", "apabila",
        "bagi", "antara", "serta", "suatu", "sebuah", "para", "adapun",
        "maupun", "per", "atas", "terhadap", "mengenai", "sesuai",
        "berdasarkan", "dimaksud", "sebagaimana", "hal", "tersebut",
    }
)

LEGAL_TERMS = frozenset(
    {
        "pasal", "ayat", "huruf", "pkwt", "pkwtt", "phk", "lembur", "pesangon",
        "kompensasi", "upah", "kontrak", "pekerja", "buruh", "alih", "daya",
        "outsourcing", "cuti", "istirahat", "waktu", "kerja", "hubungan",
        "pemutusan", "perjanjian", "perusahaan", "pengusaha", "kompensasi",
        "pesangon", "ump", "thr", "pensiun", "skorsing", "mangkir",
    }
)


# ---------------------------------------------------------------------------
# Text / query utilities
# ---------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """Normalisasi ringan untuk perbandingan dan deduplikasi chunk."""
    normalized = unicodedata.normalize("NFKC", text or "")
    return re.sub(r"\s+", " ", normalized).strip().lower()


def clean_pdf_artifacts(text: str) -> str:
    """Buang header halaman PDF seperti '2021, No.45 -16-'.

    Header ini sering terbaca model sebagai bagian kalimat dan menyebabkan
    sitasi aneh seperti "Pasal 2021, No.45 -10- (2)".
    """
    return PDF_PAGE_HEADER_RE.sub("", text or "").strip()


def build_citation_snippet(text: str, max_chars: int = 500) -> str:
    """Pilih potongan teks yang menampilkan pasal relevan, bukan header.

    Jika judul pasal berada jauh di dalam chunk (karena chunk diawali sisa
    pasal sebelumnya), snippet dimulai dari judul pasal tersebut.
    """
    cleaned = clean_pdf_artifacts(text)
    heading = re.search(r"\bpasal\s+\d+\b", cleaned, re.IGNORECASE)
    start = heading.start() if heading and heading.start() > 160 else 0
    return cleaned[start : start + max_chars].strip()


def tokenize_indonesian(text: str) -> List[str]:
    """Tokenizer BM25 sederhana: lowercase, buang tanda baca dan stopword.

    Tokenizer bawaan rank_bm25 hanya melakukan ``text.lower().split()`` sehingga
    "Pasal 26." tidak cocok dengan query "pasal 26". Normalisasi ini membuat
    pencocokan nomor pasal dan istilah hukum lebih stabil.
    """
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    tokens = WORD_RE.findall(normalized)
    return [
        token
        for token in tokens
        if (token not in INDONESIAN_STOPWORDS and len(token) > 1)
        or token.isdigit()
        or token in {"a", "b", "c", "d", "e"}
    ]


def document_key(document: Document) -> str:
    """Kunci stabil berdasarkan isi chunk, bukan metadata."""
    return hashlib.sha1(normalize_text(document.page_content).encode("utf-8")).hexdigest()


def extract_pasal_refs(text: str) -> List[Tuple[int, Optional[int]]]:
    """Ambil rujukan pasal/ayat dari teks, mis. 'Pasal 26 ayat (1)'.

    Untuk isi dokumen, ayat sering berada di baris berikutnya sehingga hanya
    nomor pasal yang biasanya tertangkap. Untuk query pengguna, format
    "Pasal 26 ayat (1)" akan menghasilkan ``(26, 1)``.
    """
    refs: List[Tuple[int, Optional[int]]] = []
    seen = set()
    for match in PASAL_REF_RE.finditer(text or ""):
        pasal = int(match.group(1))
        ayat = int(match.group(2)) if match.group(2) else None
        key = (pasal, ayat)
        if key not in seen:
            seen.add(key)
            refs.append(key)
    return refs


def extract_pasal_numbers(text: str) -> List[int]:
    """Daftar nomor pasal unik yang disebut dalam sebuah teks."""
    return sorted({pasal for pasal, _ in extract_pasal_refs(text)})


def extract_pasal_headings(text: str) -> List[int]:
    """Ambil nomor pasal yang muncul sebagai judul, bukan sebagai rujukan.

    Perbedaan ini penting: chunk Pasal 26 sering memuat frasa "sebagaimana
    dimaksud dalam Pasal 21 ayat (2)". Tanpa filter, Pasal 21 akan dianggap
    bagian dari chunk dan mencemari exact-pasal resolver.
    """
    return sorted(
        {int(match.group(1)) for match in PASAL_HEADING_RE.finditer(text or "")}
    )


def enrich_documents_with_pasal_context(
    documents: Sequence[Document],
) -> List[Document]:
    """Lengkapi metadata pasal, termasuk untuk chunk lanjutan.

    Chunk seperti ayat (2)-(4) Pasal 40 tidak selalu memuat judul "Pasal 40"
    karena terpotong chunker. Konteks pasal diwarisi dari chunk sebelumnya
    selama masih satu sumber dan halaman yang sama/bersebelahan.
    """
    active_pasal_by_source: Dict[str, int] = {}
    previous_by_source: Dict[str, Document] = {}

    for index, document in enumerate(documents):
        source = str(document.metadata.get("source", ""))
        headings = extract_pasal_headings(document.page_content)
        inherited_refs: List[int] = []
        inherited = False

        previous = previous_by_source.get(source)
        active_pasal = active_pasal_by_source.get(source)
        if previous is not None and active_pasal is not None:
            previous_page = previous.metadata.get("page")
            current_page = document.metadata.get("page")
            pages_are_adjacent = (
                not isinstance(previous_page, int)
                or not isinstance(current_page, int)
                or 0 <= current_page - previous_page <= 1
            )
            if pages_are_adjacent and active_pasal not in headings:
                inherited_refs = [active_pasal]
                inherited = True

        if headings:
            # Pasal berikutnya melanjutkan judul terakhir yang muncul dalam
            # chunk ini (nomor pasal pada UU selalu naik).
            active_pasal_by_source[source] = headings[-1]

        metadata = dict(document.metadata or {})
        metadata["chunk_index"] = index
        metadata["pasal_refs"] = sorted(set(headings + inherited_refs))
        metadata["pasal_primary"] = headings
        metadata["pasal_explicit"] = bool(headings)
        metadata["pasal_inherited"] = inherited
        document.metadata = metadata
        previous_by_source[source] = document

    return list(documents)


def deduplicate_documents(documents: Sequence[Document]) -> List[Document]:
    """Buang chunk dengan isi identik (sering muncul dari BM25 + dense)."""
    seen = set()
    result: List[Document] = []
    for document in documents:
        key = document_key(document)
        if key in seen:
            continue
        seen.add(key)
        result.append(document)
    return result


# ---------------------------------------------------------------------------
# Fusion / selection
# ---------------------------------------------------------------------------
def reciprocal_rank_fusion(
    ranked_lists: Sequence[Tuple[Sequence[Document], float, str]],
    k: int = 60,
) -> List[Document]:
    """Gabungkan beberapa ranking dengan weighted Reciprocal Rank Fusion.

    RRF dipilih karena tidak membutuhkan normalisasi skor antar-retriever:
    hanya posisi (rank) yang dipakai. Ini penting karena skor BM25 dan cosine
    Chroma tidak berada pada skala yang sama.
    """
    scores: Dict[str, float] = defaultdict(float)
    documents_by_key: Dict[str, Document] = {}
    sources_by_key: Dict[str, set] = defaultdict(set)

    for documents, weight, source in ranked_lists:
        for rank, document in enumerate(deduplicate_documents(documents)):
            key = document_key(document)
            scores[key] += weight / (k + rank + 1)
            documents_by_key.setdefault(key, document)
            sources_by_key[key].add(source)

    fused: List[Document] = []
    for key in sorted(scores, key=lambda item: scores[item], reverse=True):
        document = documents_by_key[key]
        metadata = dict(document.metadata or {})
        metadata["rrf_score"] = round(scores[key], 6)
        metadata["retrieval_sources"] = sorted(sources_by_key[key])
        fused.append(Document(page_content=document.page_content, metadata=metadata))
    return fused


def resolve_exact_pasal_documents(
    query: str,
    documents: Sequence[Document],
    limit: int = RETRIEVAL_EXACT_PASAL_LIMIT,
    include_neighbors: bool = True,
) -> List[Document]:
    """Cari chunk yang benar-benar memuat pasal/ayat yang disebut di query.

    Ini menambal kelemahan utama semantic search di domain hukum: query
    "Pasal 26 ayat (1)" bisa kalah oleh chunk lain yang secara semantik mirip
    tetapi tidak memuat pasal tersebut. Karena korpus hanya ~101 chunk,
    pemindaian penuh masih sangat murah.
    """
    refs = extract_pasal_refs(query)
    if not refs:
        return []

    targets = {pasal for pasal, _ in refs}
    ayat_by_pasal = {pasal: ayat for pasal, ayat in refs if ayat is not None}

    scored: List[Tuple[float, int, Document]] = []
    for index, document in enumerate(documents):
        text = document.page_content or ""
        document_pasal = set(
            document.metadata.get("pasal_refs") or extract_pasal_numbers(text)
        )
        matched = targets & document_pasal
        if not matched:
            continue

        primary_pasal = set(document.metadata.get("pasal_primary") or [])
        score = 0.0
        for pasal in matched:
            # Judul pasal di chunk ini lebih kuat daripada pasal yang hanya
            # diwarisi dari chunk sebelumnya atau muncul sebagai rujukan.
            score += 2.0 if pasal in primary_pasal else 0.75
            requested_ayat = ayat_by_pasal.get(pasal)
            if requested_ayat is not None:
                # PDF sering menulis "Pasal 26 \n(1)" tanpa kata "ayat".
                # Cek juga "(n)" dalam 400 karakter setelah judul pasal.
                pasal_match = re.search(
                    rf"\bpasal\s+{pasal}\b", text, re.IGNORECASE
                )
                ayat_match = re.search(
                    rf"\bayat\s*\(\s*{requested_ayat}\s*\)", text, re.IGNORECASE
                )
                nearby_ayat_match = False
                if pasal_match is not None:
                    window = text[pasal_match.start() : pasal_match.start() + 400]
                    nearby_ayat_match = bool(
                        re.search(
                            rf"\(\s*{requested_ayat}\s*\)", window, re.IGNORECASE
                        )
                    )
                if ayat_match or nearby_ayat_match:
                    score += 1.0
            if re.search(rf"\bpasal\s+{pasal}\b", text, re.IGNORECASE):
                score += 0.25

        source_name = os.path.basename(str(document.metadata.get("source", ""))).lower()
        if "penjelasan" not in source_name:
            score += 0.25
        scored.append((score, index, document))

    scored.sort(key=lambda item: (-item[0], item[1]))

    selected: List[Document] = []
    seen = set()

    def add(document: Document) -> None:
        key = document_key(document)
        if key in seen:
            return
        seen.add(key)
        selected.append(document)

    for _, _, document in scored:
        add(document)
        if len(selected) >= limit:
            break

    # Artikel hukum sering terpotong di batas chunk. Tambahkan tetangga
    # (halaman yang sama atau bersebelahan) setelah match langsung.
    if include_neighbors:
        for _, index, document in scored:
            if len(selected) >= limit:
                break
            source = document.metadata.get("source")
            page = document.metadata.get("page")
            for neighbor_index in (index - 1, index + 1):
                if neighbor_index < 0 or neighbor_index >= len(documents):
                    continue
                neighbor = documents[neighbor_index]
                if neighbor.metadata.get("source") != source:
                    continue
                neighbor_page = neighbor.metadata.get("page")
                if (
                    isinstance(page, int)
                    and isinstance(neighbor_page, int)
                    and abs(page - neighbor_page) > 1
                ):
                    continue
                add(neighbor)
                if len(selected) >= limit:
                    break

    return selected[:limit]


def select_diverse_documents(
    documents: Sequence[Document],
    limit: int,
    max_per_page: int = RETRIEVAL_MAX_PER_PAGE,
) -> List[Document]:
    """Batasi jumlah chunk per halaman agar konteks tidak redundan.

    Jika batas membuat hasil kurang dari ``limit``, sisa slot diisi dari
    overflow sehingga jumlah konteks tidak berkurang.
    """
    selected: List[Document] = []
    overflow: List[Document] = []
    counts: Dict[Tuple[Any, Any], int] = defaultdict(int)

    for document in documents:
        if len(selected) >= limit:
            break
        page_key = (
            document.metadata.get("source"),
            document.metadata.get("page"),
        )
        if counts[page_key] < max_per_page:
            counts[page_key] += 1
            selected.append(document)
        else:
            overflow.append(document)

    if len(selected) < limit:
        for document in overflow:
            selected.append(document)
            if len(selected) >= limit:
                break

    return selected[:limit]


# ---------------------------------------------------------------------------
# Reranker
# ---------------------------------------------------------------------------
class OpenRouterReranker(BaseDocumentCompressor):
    """Cross-encoder reranker via OpenRouter's /rerank endpoint."""

    model: str = Field(default=RERANKER_MODEL_NAME)
    top_n: int = Field(default=RETRIEVAL_FINAL_K)
    api_key: Optional[str] = Field(default=None)
    endpoint: str = Field(default=f"{OPENROUTER_BASE_URL.rstrip('/')}/rerank")
    timeout: int = Field(default=RERANKER_TIMEOUT)
    max_doc_chars: int = Field(default=4000)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        if not documents:
            return []

        doc_list = deduplicate_documents(documents)
        effective_k = min(self.top_n, len(doc_list))

        # Tidak ada gunanya memanggil API jika semua kandidat akan lolos.
        if len(doc_list) <= effective_k:
            return doc_list

        api_key = self.api_key or OPENROUTER_API_KEY or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning(
                "OPENROUTER_API_KEY belum disetel; memakai urutan RRF tanpa rerank."
            )
            return doc_list[:effective_k]

        candidate_models = [self.model]
        if not self.model.endswith(":free"):
            candidate_models.append(f"{self.model}:free")
        else:
            candidate_models.append(self.model.replace(":free", ""))

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kawankerja-ai",
            "X-Title": "KawanKerja AI Reranker",
        }
        doc_texts = [
            (document.page_content or "")[: self.max_doc_chars]
            for document in doc_list
        ]

        for target_model in candidate_models:
            payload = {
                "model": target_model,
                "query": query,
                "documents": doc_texts,
                "top_n": effective_k,
            }
            try:
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    logger.warning(
                        "OpenRouter rerank (%s) HTTP %s: %s",
                        target_model,
                        response.status_code,
                        response.text[:300],
                    )
                    continue

                results = response.json().get("results") or []
                ranked_documents: List[Document] = []
                used_indexes = set()
                for item in results:
                    index = item.get("index")
                    if (
                        index is None
                        or index in used_indexes
                        or not 0 <= index < len(doc_list)
                    ):
                        continue
                    used_indexes.add(index)
                    source_document = doc_list[index]
                    metadata = dict(source_document.metadata or {})
                    metadata["rerank_score"] = float(
                        item.get("relevance_score", 0.0)
                    )
                    metadata["reranker_model"] = target_model
                    ranked_documents.append(
                        Document(
                            page_content=source_document.page_content,
                            metadata=metadata,
                        )
                    )

                if ranked_documents:
                    return ranked_documents[:effective_k]
            except Exception as exc:  # noqa: BLE001 - fallback harus tetap jalan
                logger.warning(
                    "Gagal menghubungi OpenRouter reranker (%s): %s",
                    target_model,
                    exc,
                )

        logger.warning("Reranker gagal; memakai urutan RRF.")
        return doc_list[:effective_k]


# Alias lama agar kode/pengguna yang sudah mengimpor nama ini tidak pecah.
OpenRouterNemotronReranker = OpenRouterReranker


# ---------------------------------------------------------------------------
# Hybrid retriever
# ---------------------------------------------------------------------------
class LegalHybridRetriever(BaseRetriever):
    """BM25 + dense + exact-pasal + RRF + rerank + diversity."""

    dense_retriever: BaseRetriever
    bm25_retriever: Optional[BaseRetriever] = None
    reranker: Optional[BaseDocumentCompressor] = None
    all_docs: List[Document] = Field(default_factory=list)
    llm: Optional[Any] = None

    final_k: int = Field(default=RETRIEVAL_FINAL_K)
    fetch_k: int = Field(default=RETRIEVAL_FETCH_K)
    rerank_candidates: int = Field(default=RETRIEVAL_RERANK_CANDIDATES)
    bm25_weight: float = Field(default=RETRIEVAL_BM25_WEIGHT)
    dense_weight: float = Field(default=RETRIEVAL_DENSE_WEIGHT)
    exact_pasal_weight: float = Field(default=RETRIEVAL_EXACT_PASAL_WEIGHT)
    exact_pasal_limit: int = Field(default=RETRIEVAL_EXACT_PASAL_LIMIT)
    max_per_page: int = Field(default=RETRIEVAL_MAX_PER_PAGE)
    enable_query_expansion: bool = Field(default=RETRIEVAL_ENABLE_QUERY_EXPANSION)

    def model_post_init(self, __context: Any) -> None:
        """Lengkapi metadata chunk agar exact-pasal resolver bisa bekerja."""
        enrich_documents_with_pasal_context(self.all_docs)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        query = (query or "").strip()
        if not query:
            return []

        config = None
        if run_manager is not None:
            config = {"callbacks": run_manager.get_child()}

        queries: List[Tuple[str, float]] = [(query, 1.0)]
        for expanded_query in self._expand_queries(query, config=config):
            queries.append((expanded_query, 0.7))

        ranked_lists: List[Tuple[Sequence[Document], float, str]] = []
        for current_query, query_weight in queries:
            ranked_lists.extend(
                self._retrieve_once(current_query, query_weight, config=config)
            )

        exact_documents = resolve_exact_pasal_documents(
            query, self.all_docs, limit=self.exact_pasal_limit
        )
        if exact_documents:
            ranked_lists.append(
                (exact_documents, self.exact_pasal_weight, "exact_pasal")
            )

        if not ranked_lists:
            return []

        fused = reciprocal_rank_fusion(ranked_lists)
        if not fused:
            return []

        candidate_limit = max(self.rerank_candidates, self.final_k)
        candidates = fused[:candidate_limit]

        if self.reranker is not None:
            try:
                candidates = list(
                    self.reranker.compress_documents(candidates, query)
                )
            except Exception:  # noqa: BLE001 - retrieval harus tetap jalan
                logger.exception("Reranker gagal; memakai urutan RRF.")

        return select_diverse_documents(
            candidates, limit=self.final_k, max_per_page=self.max_per_page
        )

    def _retrieve_once(
        self,
        query: str,
        query_weight: float,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Sequence[Document], float, str]]:
        results: List[Tuple[Sequence[Document], float, str]] = []

        if self.bm25_retriever is not None:
            try:
                bm25_documents = self.bm25_retriever.invoke(query, config=config)
                if bm25_documents:
                    results.append(
                        (
                            bm25_documents,
                            query_weight * self.bm25_weight,
                            "bm25",
                        )
                    )
            except Exception:  # noqa: BLE001
                logger.exception("BM25 retrieval gagal untuk query: %s", query[:80])

        try:
            dense_documents = self.dense_retriever.invoke(query, config=config)
            if dense_documents:
                results.append(
                    (
                        dense_documents,
                        query_weight * self.dense_weight,
                        "dense",
                    )
                )
        except Exception:  # noqa: BLE001
            logger.exception("Dense retrieval gagal untuk query: %s", query[:80])

        return results

    def _is_vague_query(self, query: str) -> bool:
        normalized = query.lower()
        if len(WORD_RE.findall(normalized)) >= 12:
            return False
        if PASAL_REF_RE.search(normalized):
            return False
        return not any(term in normalized for term in LEGAL_TERMS)

    def _expand_queries(
        self,
        query: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        if not self.enable_query_expansion or self.llm is None:
            return []
        if not self._is_vague_query(query):
            return []

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Anda adalah asisten pencarian dokumen hukum Indonesia. "
                    "Ubah pertanyaan pengguna menjadi maksimal 2 variasi query "
                    "pencarian yang lebih spesifik dengan istilah hukum "
                    "ketenagakerjaan yang lazim (PKWT, PHK, pesangon, lembur, "
                    "upah, alih daya). Jangan menjawab pertanyaan. Keluarkan "
                    "satu query per baris, tanpa nomor dan tanpa penjelasan.",
                ),
                ("human", "{question}"),
            ]
        )

        try:
            message = (prompt | self.llm).invoke(
                {"question": query}, config=config
            )
        except Exception:  # noqa: BLE001
            logger.warning("Query expansion gagal; memakai query asli.", exc_info=True)
            return []

        content = getattr(message, "content", message)
        if not isinstance(content, str):
            return []

        expanded: List[str] = []
        for line in content.splitlines():
            candidate = line.strip().strip("\"'*-•").strip()
            candidate = re.sub(r"^\d+[.)]\s*", "", candidate).strip()
            if not candidate or candidate.lower() == query.lower():
                continue
            if not 4 <= len(candidate) <= 240:
                continue
            if candidate not in expanded:
                expanded.append(candidate)
            if len(expanded) >= 2:
                break
        return expanded


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def _document_page_sort_key(document: Document) -> Tuple[str, int]:
    page = document.metadata.get("page", 0)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 0
    return str(document.metadata.get("source", "")), page


def get_advanced_retriever(
    llm,
    search_type: str = "similarity",
    final_k: Optional[int] = None,
    fetch_k: Optional[int] = None,
    persist_directory: Optional[str] = None,
    collection_name: str = "langchain",
    enable_reranker: Optional[bool] = None,
    enable_query_expansion: Optional[bool] = None,
):
    """Bangun retriever hybrid yang sesuai untuk korpus kecil.

    Args:
        llm: LLM opsional, hanya dipakai jika query expansion diaktifkan.
        search_type: Tipe pencarian Chroma, default ``similarity``.
        final_k: Jumlah konteks akhir yang dikirim ke prompt.
        fetch_k: Jumlah kandidat per retriever sebelum fusion.
        persist_directory: Lokasi ChromaDB.
        collection_name: Nama koleksi ChromaDB.
        enable_reranker: None mengikuti RETRIEVAL_ENABLE_RERANKER. Default
            mati untuk korpus kecil; aktifkan jika korpus membesar.
        enable_query_expansion: Override konfigurasi query expansion.
    """
    final_k = RETRIEVAL_FINAL_K if final_k is None else final_k
    fetch_k = RETRIEVAL_FETCH_K if fetch_k is None else fetch_k
    if enable_reranker is None:
        enable_reranker = RETRIEVAL_ENABLE_RERANKER
    if enable_query_expansion is None:
        enable_query_expansion = RETRIEVAL_ENABLE_QUERY_EXPANSION
    if persist_directory is None:
        persist_directory = str(CHROMA_DB_DIR)

    logger.info(
        "Menyiapkan retriever hybrid (fetch_k=%s, rerank=%s, final_k=%s).",
        fetch_k,
        enable_reranker,
        final_k,
    )

    embeddings = get_embedding_model()
    vector_store = Chroma(
        collection_name=collection_name,
        persist_directory=persist_directory,
        embedding_function=embeddings,
    )

    db_data = vector_store.get()
    raw_documents = db_data.get("documents") or []
    metadatas = db_data.get("metadatas") or []
    documents = [
        Document(page_content=text, metadata=dict(metadata or {}))
        for text, metadata in zip(raw_documents, metadatas)
    ]
    documents.sort(key=_document_page_sort_key)
    enrich_documents_with_pasal_context(documents)

    num_docs = len(documents)
    safe_fetch_k = max(1, min(fetch_k, num_docs)) if num_docs else 1

    dense_retriever = vector_store.as_retriever(
        search_type=search_type,
        search_kwargs={"k": safe_fetch_k},
    )

    bm25_retriever: Optional[BM25Retriever] = None
    if documents:
        bm25_retriever = BM25Retriever.from_documents(
            documents,
            preprocess_func=tokenize_indonesian,
        )
        bm25_retriever.k = safe_fetch_k

    reranker = (
        OpenRouterReranker(top_n=final_k) if enable_reranker else None
    )
    rerank_candidates = max(
        final_k,
        min(RETRIEVAL_RERANK_CANDIDATES, num_docs) if num_docs else final_k,
    )

    return LegalHybridRetriever(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
        reranker=reranker,
        all_docs=documents,
        llm=llm,
        final_k=final_k,
        fetch_k=safe_fetch_k,
        rerank_candidates=rerank_candidates,
        bm25_weight=RETRIEVAL_BM25_WEIGHT,
        dense_weight=RETRIEVAL_DENSE_WEIGHT,
        exact_pasal_weight=RETRIEVAL_EXACT_PASAL_WEIGHT,
        exact_pasal_limit=RETRIEVAL_EXACT_PASAL_LIMIT,
        max_per_page=RETRIEVAL_MAX_PER_PAGE,
        enable_query_expansion=enable_query_expansion,
    )


# ======= Blok testing =======
if __name__ == "__main__":
    test_docs = [
        Document(
            page_content="Pasal 26 (1) Waktu Kerja Lembur paling lama 4 jam sehari dan 18 jam seminggu.",
            metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 15},
        ),
        Document(
            page_content="Pasal 8 (1) PKWT berdasarkan jangka waktu paling lama 5 tahun.",
            metadata={"source": "PP_No_35_Tahun_2021.pdf", "page": 6},
        ),
        Document(
            page_content="Budidaya lele dumbo membutuhkan pH air optimal 6.5 sampai 8.",
            metadata={"source": "Perikanan.pdf", "page": 1},
        ),
    ]

    print("Token BM25:", tokenize_indonesian("Berapa Pasal 26 ayat (1)?"))
    print("Ref query:", extract_pasal_refs("Pasal 26 ayat (1) dan Pasal 8"))
    exact = resolve_exact_pasal_documents("Pasal 26 ayat (1)", test_docs)
    print("\n[HASIL EXACT PASAL]")
    for item in exact:
        print(f"- {item.page_content[:90]}...")
