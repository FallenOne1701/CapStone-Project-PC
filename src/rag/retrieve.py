from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import Settings
from src.ingest.index import COLLECTION_NAME
from src.schemes import detect_scheme_id

# Longer / more specific needles first.
_SECTION_HINTS: tuple[tuple[str, str], ...] = (
    ("expense ratio", "expense ratio"),
    ("investment objective", "investment objective"),
    ("exit load", "exit load"),
    ("minimum sip", "minimum sip"),
    ("min sip", "minimum sip"),
    ("lump sum", "minimum lumpsum"),
    ("lumpsum", "minimum lumpsum"),
    ("lock-in", "lock-in"),
    ("lock in", "lock-in"),
    ("lockin", "lock-in"),
    ("stamp duty", "stamp duty"),
    ("riskometer", "riskometer"),
    ("benchmark", "benchmark"),
    ("objective", "investment objective"),
    ("expense", "expense ratio"),
    ("category", "category"),
    ("sip", "minimum sip"),
    ("risk", "riskometer"),
    ("nav", "nav"),
)


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source_url: str
    as_of_date: str
    scheme_id: str
    section: str
    score: float  # cosine similarity in [0, 1] = 1 - chroma_distance


def detect_section(query: str) -> Optional[str]:
    q = query.lower()
    for needle, section in _SECTION_HINTS:
        if needle in q:
            return section
    return None


def _build_where(
    scheme_id: Optional[str], section: Optional[str]
) -> Optional[dict]:
    if scheme_id and section:
        return {"$and": [{"scheme_id": scheme_id}, {"section": section}]}
    if scheme_id:
        return {"scheme_id": scheme_id}
    if section:
        return {"section": section}
    return None


def _rows_to_chunks(
    documents: list[str],
    metadatas: list[dict],
    distances: list[float],
    threshold: float,
) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for text, meta, dist in zip(documents, metadatas, distances):
        score = 1.0 - float(dist)
        if score < threshold:
            continue
        chunks.append(
            RetrievedChunk(
                text=text,
                source_url=str(meta["source_url"]),
                as_of_date=str(meta["as_of_date"]),
                scheme_id=str(meta["scheme_id"]),
                section=str(meta["section"]),
                score=score,
            )
        )
    chunks.sort(key=lambda c: c.score, reverse=True)
    return chunks


def _query_collection(
    collection,
    embedding: list[float],
    where: Optional[dict],
    n_results: int,
) -> tuple[list[str], list[dict], list[float]]:
    kwargs: dict = {
        "query_embeddings": [embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        kwargs["where"] = where
    result = collection.query(**kwargs)
    docs = result["documents"][0] if result["documents"] else []
    metas = result["metadatas"][0] if result["metadatas"] else []
    dists = result["distances"][0] if result["distances"] else []
    return docs, metas, dists


def retrieve(
    query: str,
    settings: Settings,
    scheme_id: Optional[str] = None,
) -> list[RetrievedChunk]:
    resolved_scheme = scheme_id if scheme_id is not None else detect_scheme_id(query)
    section = detect_section(query)
    where = _build_where(resolved_scheme, section)

    n_results = settings.top_k
    if resolved_scheme and section:
        n_results = min(settings.top_k, 2)

    model = SentenceTransformer(settings.embed_model)
    embedding = list(map(float, model.encode([query], show_progress_bar=False)[0]))

    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = client.get_collection(COLLECTION_NAME)

    docs, metas, dists = _query_collection(collection, embedding, where, n_results)
    chunks = _rows_to_chunks(docs, metas, dists, settings.similarity_threshold)

    # Widen once: drop section filter if scheme known and nothing kept.
    if not chunks and section and resolved_scheme and where is not None:
        widen_where = {"scheme_id": resolved_scheme}
        docs, metas, dists = _query_collection(
            collection, embedding, widen_where, settings.top_k
        )
        chunks = _rows_to_chunks(docs, metas, dists, settings.similarity_threshold)

    return chunks
