from __future__ import annotations

from dataclasses import dataclass, field

from src.clean import EMAIL_RE, PHONE_RE
from src.models import PulseDoc, Review
from src.write_pulse import count_words


@dataclass
class AuditResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def _quote_grounded(quote: str, reviews: list[Review]) -> bool:
    q = quote.strip().strip('"').strip("'")
    if not q:
        return False
    for r in reviews:
        if q in r.text:
            return True
    return False


def audit_pulse(doc: PulseDoc, reviews: list[Review], max_words: int = 250) -> AuditResult:
    errors: list[str] = []
    if len(doc.themes) != 3:
        errors.append(f"expected 3 themes, got {len(doc.themes)}")
    if len(doc.quotes) != 3:
        errors.append(f"expected 3 quotes, got {len(doc.quotes)}")
    if len(doc.actions) != 3:
        errors.append(f"expected 3 actions, got {len(doc.actions)}")
    for i, q in enumerate(doc.quotes):
        if not _quote_grounded(q, reviews):
            errors.append(f"quote[{i}] not grounded in cleaned reviews")
    blob = "\n".join([doc.body_markdown, *doc.quotes, *doc.actions, *doc.themes])
    if EMAIL_RE.search(blob) or PHONE_RE.search(blob):
        errors.append("PII pattern detected in pulse artifact")
    words = count_words(doc.body_markdown)
    if words > max_words:
        errors.append(f"body word count {words} exceeds {max_words}")
    if doc.review_count <= 0:
        errors.append("review_count must be > 0")
    return AuditResult(ok=not errors, errors=errors)
