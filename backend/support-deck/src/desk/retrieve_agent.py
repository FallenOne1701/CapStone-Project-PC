from __future__ import annotations

from src.desk import faq_client
from src.desk.faq_client import RetrieveResult


def run_retrieve(q: str) -> RetrieveResult:
    """Query FAQ corpus via faq_client; always populate a non-empty ``searched`` list."""
    result = faq_client.faq_retrieve(q or "")
    searched = list(result.searched) if result.searched else []
    if not searched:
        searched.append("FAQ corpus")
        label = (q or "").strip()
        if label:
            searched.append(f"query:{label[:80]}")
    return RetrieveResult(
        chunks=list(result.chunks),
        source_urls=list(result.source_urls),
        searched=searched,
    )
