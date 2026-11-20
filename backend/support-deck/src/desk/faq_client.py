from __future__ import annotations

import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from src.config import get_settings

# Backend and Support Deck both use a top-level ``src`` package. Swapping
# ``sys.modules`` must be exclusive — otherwise parallel FastAPI requests
# (or policy∥retrieve threads) see ``ModuleNotFoundError: src.api.deps``
# and the browser reports a generic "Failed to fetch".
_BACKEND_IMPORT_LOCK = threading.Lock()

# backend/src/config.py load_dotenv sets GROQ_BASE_URL=.../openai/v1, which
# breaks langchain_groq (double /openai/v1 path). Snapshot + restore.
_GROQ_ENV_KEYS = ("GROQ_BASE_URL",)


@dataclass
class RetrieveResult:
    chunks: list[dict[str, Any]] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    searched: list[str] = field(default_factory=list)


@contextmanager
def _backend_import_context() -> Iterator[None]:
    """Prepend BACKEND_ROOT and isolate `src.*` so backend imports do not collide."""
    with _BACKEND_IMPORT_LOCK:
        backend_root = str(Path(get_settings().backend_root).resolve())
        stashed = {
            key: sys.modules.pop(key)
            for key in list(sys.modules)
            if key == "src" or key.startswith("src.")
        }
        env_snapshot = {key: os.environ.get(key) for key in _GROQ_ENV_KEYS}
        inserted = False
        if backend_root not in sys.path:
            sys.path.insert(0, backend_root)
            inserted = True
        try:
            yield
        finally:
            for key in list(sys.modules):
                if key == "src" or key.startswith("src."):
                    sys.modules.pop(key, None)
            if inserted:
                try:
                    sys.path.remove(backend_root)
                except ValueError:
                    pass
            sys.modules.update(stashed)
            for key, value in env_snapshot.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


def _backend_retrieve(
    question: str,
) -> tuple[list[Any], str | None, str | None]:
    with _backend_import_context():
        from src.config import get_settings as backend_get_settings
        from src.rag.retrieve import detect_section, retrieve
        from src.schemes import detect_scheme_id

        settings = backend_get_settings()
        scheme_id = detect_scheme_id(question)
        section = detect_section(question)
        chunks = retrieve(question, settings, scheme_id=scheme_id)
        return chunks, scheme_id, section


def _backend_classify(question: str) -> Any:
    with _backend_import_context():
        from src.rag.classify import classify

        # Rules-only when settings omitted; avoids Groq for adapter default path
        return classify(question, settings=None)


def _build_searched(
    question: str,
    scheme_id: str | None,
    section: str | None,
    source_urls: list[str],
) -> list[str]:
    searched: list[str] = []
    if scheme_id:
        searched.append(f"scheme:{scheme_id}")
    if section:
        searched.append(f"section:{section}")
    searched.append("FAQ corpus")
    for url in source_urls:
        if url not in searched:
            searched.append(url)
    # Always non-empty; include a short question label for audit trails
    q = question.strip()
    if q and q not in searched:
        searched.append(f"query:{q[:80]}")
    return searched


def faq_retrieve(question: str) -> RetrieveResult:
    raw_chunks, scheme_id, section = _backend_retrieve(question)
    chunks: list[dict[str, Any]] = []
    source_urls: list[str] = []
    for chunk in raw_chunks:
        url = str(getattr(chunk, "source_url", "") or "")
        chunks.append(
            {
                "text": str(getattr(chunk, "text", "")),
                "source_url": url,
                "as_of_date": str(getattr(chunk, "as_of_date", "")),
                "scheme_id": str(getattr(chunk, "scheme_id", "")),
                "section": str(getattr(chunk, "section", "")),
                "score": float(getattr(chunk, "score", 0.0)),
            }
        )
        if url and url not in source_urls:
            source_urls.append(url)
    searched = _build_searched(question, scheme_id, section, source_urls)
    return RetrieveResult(chunks=chunks, source_urls=source_urls, searched=searched)


def faq_classify(question: str) -> str:
    intent = _backend_classify(question)
    if hasattr(intent, "value"):
        return str(intent.value)
    return str(intent)
