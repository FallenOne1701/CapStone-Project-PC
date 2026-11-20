from __future__ import annotations

import re

# Indian PAN: five letters, four digits, one letter (e.g. ABCDE1234F)
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)

# Email
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

# Indian mobile: optional +91 / 0 prefix, then 10 digits starting 6–9
_PHONE = re.compile(
    r"(?<!\d)(?:\+?91[\s-]*)?0?[6-9]\d{9}(?!\d)"
)

# Account-like: 9–18 contiguous digits (covers many bank account forms)
_ACCOUNT = re.compile(r"(?<!\d)\d{9,18}(?!\d)")

_PATTERNS: tuple[re.Pattern[str], ...] = (_PAN, _EMAIL, _PHONE, _ACCOUNT)

_REDACT = "[REDACTED]"


def contains_pii(text: str) -> bool:
    if not text:
        return False
    return any(p.search(text) for p in _PATTERNS)


def redact_pii(text: str) -> str:
    if not text:
        return text
    out = text
    for pattern in _PATTERNS:
        out = pattern.sub(_REDACT, out)
    return out
