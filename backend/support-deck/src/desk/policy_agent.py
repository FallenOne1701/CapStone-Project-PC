from __future__ import annotations

from dataclasses import dataclass, field

from src.pii import contains_pii

# Deterministic cues (aligned with backend refuse patterns; fail closed)
_ADVICE_CUES = (
    "should i",
    "should we",
    "recommend",
    "advice",
    "suitable for",
    "is it good",
    "good investment",
    "buy this",
    "buy it",
    "sell this",
    "sell it",
    "worth buying",
    "can i buy",
    "should i invest",
    "should i buy",
    "buy-sell",
    "buy/sell",
)

_RETURNS_CUES = (
    "return",
    "returns",
    "cagr",
    "performance",
    "how much did",
    "past performance",
    "historical return",
)


@dataclass
class PolicyResult:
    allow: bool
    refuse: bool
    reasons: list[str] = field(default_factory=list)
    category: str = "factual"

    def __post_init__(self) -> None:
        # Keep allow/refuse mutually exclusive
        if self.refuse:
            self.allow = False
        elif self.allow:
            self.refuse = False


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def run_policy(q: str) -> PolicyResult:
    """Classify advice / returns / PII; recommend refuse or allow.

    Deterministic rules only (no LLM). Does not call draft or retrieve.
    """
    text = (q or "").strip()
    if not text:
        return PolicyResult(
            allow=False,
            refuse=True,
            reasons=["empty_question"],
            category="oos",
        )

    lower = text.lower()
    reasons: list[str] = []

    if contains_pii(text):
        reasons.append("pii_detected")
        return PolicyResult(
            allow=False, refuse=True, reasons=reasons, category="pii"
        )

    if _contains_any(lower, _ADVICE_CUES):
        reasons.append("advisory_or_advice")
        return PolicyResult(
            allow=False, refuse=True, reasons=reasons, category="advice"
        )

    if _contains_any(lower, _RETURNS_CUES):
        reasons.append("returns_or_performance")
        return PolicyResult(
            allow=False, refuse=True, reasons=reasons, category="returns"
        )

    return PolicyResult(
        allow=True, refuse=False, reasons=["factual_ok"], category="factual"
    )
