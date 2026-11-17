from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from src.config import ROOT, Settings, get_groq_client
from src.schemes import detect_scheme_id

CLASSIFIER_PROMPT_PATH = ROOT / "prompts" / "classifier.txt"

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(?:\+?91[\s-]?)?[6-9]\d{9}\b")

PII_KEYWORDS = (
    "pan is",
    "my pan",
    "aadhaar",
    "aadhar",
    "otp",
    "account number",
    "folio number",
    "my holdings",
    "my email",
    "my phone",
    "my mobile",
)

ADVISORY_CUES = (
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
)

COMPARATIVE_CUES = (
    "which is better",
    "better than",
    "compare",
    "comparison",
    " vs ",
    " versus ",
    "or mid cap",
    "or large cap",
    "or small cap",
)

PERFORMANCE_CUES = (
    "return",
    "returns",
    "cagr",
    "performance",
    "how much did",
    "past performance",
)

FACTUAL_SCHEME_CUES = (
    "expense ratio",
    "expense",
    "exit load",
    "exist load",  # common typo for exit load
    "minimum sip",
    "min sip",
    "sip",
    "lumpsum",
    "lump sum",
    "lock-in",
    "lock in",
    "lockin",
    "benchmark",
    "riskometer",
    "investment objective",
    "objective",
    "nav",
    "stamp duty",
    "category",
    "fund house",
)

FACTUAL_PROCESS_CUES = (
    "how to invest",
    "how do i invest",
    "how to redeem",
    "how to buy",
    "kyc",
    "open folio",
    "switch fund",
    "systematic withdrawal",
)

FOREIGN_AMC_CUES = (
    "sbi ",
    "sbi.",
    "icici",
    "axis ",
    "nippon",
    "uti ",
    "kotak",
    "franklin",
    "mirae",
    "parag parikh",
    "dsp ",
    "tata ",
    "motilal",
    "quant ",
)


class Intent(str, Enum):
    FACTUAL_SCHEME = "FACTUAL_SCHEME"
    FACTUAL_PROCESS = "FACTUAL_PROCESS"
    PERFORMANCE = "PERFORMANCE"
    ADVISORY = "ADVISORY"
    COMPARATIVE = "COMPARATIVE"
    PII_SENSITIVE = "PII_SENSITIVE"
    OUT_OF_CORPUS = "OUT_OF_CORPUS"
    UNCLEAR = "UNCLEAR"


def _contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def _rule_classify(query: str) -> Intent:
    q = query.lower()
    upper = query.upper()

    if (
        PAN_RE.search(upper)
        or EMAIL_RE.search(query)
        or PHONE_RE.search(query)
        or _contains_any(q, PII_KEYWORDS)
    ):
        return Intent.PII_SENSITIVE

    # Prefer false refusals: advice + fact → ADVISORY
    if _contains_any(q, ADVISORY_CUES):
        return Intent.ADVISORY

    if _contains_any(q, COMPARATIVE_CUES):
        return Intent.COMPARATIVE

    if _contains_any(q, PERFORMANCE_CUES):
        return Intent.PERFORMANCE

    scheme_id = detect_scheme_id(query)
    has_fact = _contains_any(q, FACTUAL_SCHEME_CUES)
    foreign = _contains_any(q, FOREIGN_AMC_CUES)

    if has_fact and foreign and scheme_id is None:
        return Intent.OUT_OF_CORPUS

    if has_fact and scheme_id is not None:
        return Intent.FACTUAL_SCHEME

    if has_fact and scheme_id is None and not foreign:
        # Scheme unclear — fail closed to clarify rather than mixed-scheme RAG
        return Intent.UNCLEAR

    if _contains_any(q, FACTUAL_PROCESS_CUES):
        return Intent.FACTUAL_PROCESS

    if foreign and ("fund" in q or "mutual" in q or has_fact):
        return Intent.OUT_OF_CORPUS

    if scheme_id is not None and (
        q.strip().startswith("what")
        or q.strip().startswith("how")
        or "?" in q
    ):
        return Intent.FACTUAL_SCHEME

    return Intent.UNCLEAR


def _llm_classify(query: str, settings: Settings) -> Intent:
    prompt = CLASSIFIER_PROMPT_PATH.read_text(encoding="utf-8").strip()
    client = get_groq_client(settings)
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
    )
    raw = (response.choices[0].message.content or "").strip().upper()
    for intent in Intent:
        if intent.value in raw:
            return intent
    return Intent.UNCLEAR


def classify(query: str, settings: Optional[Settings] = None) -> Intent:
    intent = _rule_classify(query)
    if intent is Intent.UNCLEAR and settings is not None:
        try:
            return _llm_classify(query, settings)
        except Exception:
            return Intent.UNCLEAR
    return intent
