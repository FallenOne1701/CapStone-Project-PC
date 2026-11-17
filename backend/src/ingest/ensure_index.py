from __future__ import annotations

import logging
import os
from pathlib import Path

import chromadb

from src.config import ROOT, Settings
from src.ingest.index import COLLECTION_NAME, build_index

logger = logging.getLogger(__name__)


def _candidate_paths(primary: Path) -> list[Path]:
    paths = [primary]
    fallback = (ROOT / "corpus_index").resolve()
    if fallback not in {p.resolve() for p in paths}:
        paths.append(fallback)
    return paths


def probe_path(path: Path) -> dict:
    info: dict = {
        "chroma_path": str(path.resolve()),
        "chroma_path_exists": path.exists(),
        "collection": COLLECTION_NAME,
        "collection_exists": False,
        "chunk_count": 0,
        "collections": [],
    }
    if not path.exists():
        return info
    try:
        client = chromadb.PersistentClient(path=str(path))
        names = [c.name for c in client.list_collections()]
        info["collections"] = names
        if COLLECTION_NAME in names:
            info["collection_exists"] = True
            info["chunk_count"] = int(client.get_collection(COLLECTION_NAME).count())
    except Exception as exc:  # pragma: no cover
        info["error"] = str(exc)
    return info


def index_status(settings: Settings | None = None) -> dict:
    if settings is None:
        # Health checks should work even if GROQ is missing.
        chroma_env = os.getenv("CHROMA_PATH", "corpus_index")
        primary = Path(chroma_env)
        if not primary.is_absolute():
            primary = ROOT / primary
        embed = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        settings = Settings(
            groq_api_key=os.getenv("GROQ_API_KEY", "missing"),
            chat_model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b"),
            groq_base_url=os.getenv(
                "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
            ),
            embed_model=embed,
            chroma_path=primary,
            similarity_threshold=0.35,
            top_k=4,
        )

    candidates = []
    for path in _candidate_paths(settings.chroma_path):
        candidates.append(probe_path(path))
    best = next(
        (c for c in candidates if c.get("collection_exists") and c.get("chunk_count", 0) > 0),
        candidates[0],
    )
    return {"active": best, "candidates": candidates}


def ensure_index(settings: Settings) -> Path:
    """Return a chroma path that has mf_faq; rebuild from processed docs if needed."""
    for path in _candidate_paths(settings.chroma_path):
        probe = probe_path(path)
        if probe.get("collection_exists") and probe.get("chunk_count", 0) > 0:
            if path.resolve() != settings.chroma_path.resolve():
                logger.warning(
                    "Using fallback Chroma path %s (configured %s)",
                    path,
                    settings.chroma_path,
                )
            return path

    processed_dir = ROOT / "data" / "processed"
    manifest_path = ROOT / "data" / "manifest.json"
    if not manifest_path.exists() or not processed_dir.is_dir():
        raise RuntimeError(
            f"Chroma collection '{COLLECTION_NAME}' missing at "
            f"{settings.chroma_path} and cannot rebuild "
            f"(need {manifest_path} + {processed_dir}). "
            "Redeploy with backend/corpus_index committed, or run "
            "`python -m src.ingest.index`."
        )

    target = settings.chroma_path
    logger.warning("Rebuilding Chroma index at %s", target)
    # Temporarily point settings at target for build_index
    rebuild_settings = Settings(
        groq_api_key=settings.groq_api_key,
        chat_model=settings.chat_model,
        groq_base_url=settings.groq_base_url,
        embed_model=settings.embed_model,
        chroma_path=target,
        similarity_threshold=settings.similarity_threshold,
        top_k=settings.top_k,
        educational_link=settings.educational_link,
    )
    n = build_index(processed_dir, manifest_path, rebuild_settings)
    probe = probe_path(target)
    if not probe.get("collection_exists"):
        raise RuntimeError(
            f"Rebuild finished ({n} chunks) but collection still missing at {target}"
        )
    return target
