from __future__ import annotations

import re
from dataclasses import dataclass, field

FOOTER_RE = re.compile(r"Last updated from sources: \d{4}-\d{2}-\d{2}")
URL_RE = re.compile(r"https://")
PAN_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
ADVICE_PHRASES = (
    "i recommend",
    "you should invest",
    "better than",
    "guaranteed returns",
    "buy this",
    "sell this",
)


@dataclass(frozen=True)
class AuditResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def audit_response(text: str) -> AuditResult:
    reasons: list[str] = []
    source_idx = text.find("Source:")
    body = text if source_idx < 0 else text[:source_idx]

    sentences = [p for p in SENTENCE_SPLIT_RE.split(body.strip()) if p]
    if len(sentences) > 3:
        reasons.append("body exceeds 3 sentences")

    url_count = len(URL_RE.findall(text))
    if url_count != 1:
        reasons.append(f"expected exactly one https URL, found {url_count}")

    if not FOOTER_RE.search(text):
        reasons.append("missing Last updated from sources footer")

    lowered = text.lower()
    for phrase in ADVICE_PHRASES:
        if phrase in lowered:
            reasons.append(f"advice phrase blocked: {phrase}")

    if PAN_RE.search(text):
        reasons.append("PAN-like pattern must not appear")

    return AuditResult(ok=not reasons, reasons=reasons)
