from __future__ import annotations

import re
from typing import Any, Literal, Optional
from urllib.parse import urlparse

from src.config import Settings
from src.schemes import SCHEMES

ResponseType = Literal["factual", "refusal"]

SOURCE_RE = re.compile(
    r"^Source:\s*(?P<url>https://\S+)\s*$", re.MULTILINE
)
FOOTER_RE = re.compile(
    r"^Last updated from sources:\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$",
    re.MULTILINE,
)
URL_RE = re.compile(r"https://[^\s)]+")


def _scheme_id_for_url(url: str) -> Optional[str]:
    for scheme_id, meta in SCHEMES.items():
        if str(meta.get("groww_url", "")) == url:
            return scheme_id
    return None


def _guess_refusal_reason(text: str) -> str:
    lower = text.lower()
    if "investment advice" in lower or "recommend" in lower:
        return "advisory"
    if "compare funds" in lower or "which is better" in lower:
        return "comparative"
    if "historical returns" in lower or "performance data" in lower:
        return "performance"
    if "personal or account" in lower or "won't store" in lower:
        return "pii"
    if "outside this assistant" in lower or "couldn't find that fact" in lower:
        return "out_of_corpus"
    if "not sure which factual" in lower:
        return "unclear"
    return "refused"


def map_answer_to_response(text: str, settings: Settings) -> dict[str, Any]:
    """Map orchestrator plain-text output to the public API JSON shape."""
    source = SOURCE_RE.search(text)
    footer = FOOTER_RE.search(text)

    if source and footer:
        citation_url = source.group("url").rstrip(".,;")
        body = text[: source.start()].strip()
        return {
            "type": "factual",
            "answer": body,
            "citation_url": citation_url,
            "last_updated": footer.group("date"),
            "scheme_id": _scheme_id_for_url(citation_url),
        }

    urls = URL_RE.findall(text)
    educational_url = settings.educational_link
    for url in urls:
        host = urlparse(url).netloc.lower()
        if "amfiindia.com" in host or "sebi.gov.in" in host:
            educational_url = url
            break
        if "groww.in" in host:
            educational_url = url
            break
    if urls and educational_url == settings.educational_link:
        educational_url = urls[0]

    return {
        "type": "refusal",
        "answer": text.strip(),
        "educational_url": educational_url,
        "reason": _guess_refusal_reason(text),
    }
