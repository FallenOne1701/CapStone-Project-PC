from __future__ import annotations

import re

from src.models import Review

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,6}"
)
HANDLE_RE = re.compile(r"@\w{2,}")


def strip_pii_text(text: str) -> str:
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = HANDLE_RE.sub("[redacted-handle]", text)
    text = PHONE_RE.sub("[redacted-phone]", text)
    return text.strip()


def clean_reviews(reviews: list[Review]) -> list[Review]:
    cleaned: list[Review] = []
    for r in reviews:
        text = strip_pii_text(r.text)
        title = strip_pii_text(r.title) if r.title else None
        if not text:
            continue
        cleaned.append(r.model_copy(update={"text": text, "title": title}))
    return cleaned
