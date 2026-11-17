from __future__ import annotations

import re
from typing import Optional

from src.config import Settings, get_settings
from src.rag.audit import audit_response
from src.rag.classify import Intent, classify
from src.rag.generate import answer_from_chunks
from src.rag.refuse import build_refusal
from src.rag.retrieve import retrieve
from src.schemes import detect_scheme_id

PAN_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
PII_HINTS = (
    "aadhaar",
    "aadhar",
    "my pan",
    "otp",
    "account number",
    "my email",
    "my phone",
    "my mobile",
    "my holdings",
)

REFUSE_INTENTS = {
    Intent.ADVISORY,
    Intent.COMPARATIVE,
    Intent.PII_SENSITIVE,
    Intent.OUT_OF_CORPUS,
    Intent.UNCLEAR,
    Intent.PERFORMANCE,
}

SAFE_FALLBACK = (
    "I couldn't produce a compliant factual answer from the corpus. "
    "Please ask a specific fact about a supported HDFC scheme "
    "(expense ratio, exit load, SIP minimum, lock-in, NAV, and similar)."
)


def _looks_like_pii(query: str) -> bool:
    if PAN_RE.search(query.upper()):
        return True
    q = query.lower()
    return any(hint in q for hint in PII_HINTS)


def _normalize_query(query: str) -> str:
    # Common typo: "exist load" → "exit load" (helps retrieval + cues).
    return re.sub(r"\bexist\s+load\b", "exit load", query, flags=re.IGNORECASE)


def answer_query(query: str, settings: Optional[Settings] = None) -> str:
    settings = settings or get_settings()
    query = _normalize_query(query)

    # Fail closed on PII before classify/retrieve; do not log the raw query.
    if _looks_like_pii(query):
        return build_refusal(Intent.PII_SENSITIVE, None, settings)

    intent = classify(query, settings)
    scheme_id = detect_scheme_id(query)

    if intent in REFUSE_INTENTS:
        return build_refusal(intent, scheme_id, settings)

    # FACTUAL_SCHEME without a resolvable scheme → ask/clarify (Task 7 policy).
    if intent is Intent.FACTUAL_SCHEME and scheme_id is None:
        return build_refusal(Intent.UNCLEAR, None, settings)

    chunks = retrieve(query, settings, scheme_id=scheme_id)
    if not chunks:
        return build_refusal(Intent.OUT_OF_CORPUS, scheme_id, settings)

    answer = answer_from_chunks(query, chunks, settings)
    if audit_response(answer).ok:
        return answer

    retry = answer_from_chunks(query, chunks, settings, strict=True)
    if audit_response(retry).ok:
        return retry

    return SAFE_FALLBACK
