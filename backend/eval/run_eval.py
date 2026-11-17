from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.audit import audit_response  # noqa: E402
from src.rag.classify import classify  # noqa: E402
from src.rag.orchestrator import answer_query  # noqa: E402
from src.config import get_settings  # noqa: E402

GOLDEN_PATH = Path(__file__).resolve().parent / "golden_questions.json"
FOOTER_RE = re.compile(r"Last updated from sources: \d{4}-\d{2}-\d{2}")
URL_RE = re.compile(r"https://")
PAN_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
GLOBAL_BLOCKLIST = (
    "i recommend",
    "you should invest",
    "guaranteed returns",
)


def _redact_query(query: str) -> str:
    return PAN_RE.sub("[PAN_REDACTED]", query)


def _check_case(case: dict[str, Any], answer: str, intent_value: str) -> list[str]:
    reasons: list[str] = []
    lowered = answer.lower()

    if case.get("expect_intent") and intent_value != case["expect_intent"]:
        reasons.append(
            f"intent_mismatch expected={case['expect_intent']} got={intent_value}"
        )

    for needle in case.get("must_include") or []:
        if needle.lower() not in lowered and needle not in answer:
            reasons.append(f"missing_include:{needle}")

    for needle in case.get("must_not_include") or []:
        if needle.lower() in lowered:
            reasons.append(f"forbidden:{needle}")

    for needle in GLOBAL_BLOCKLIST:
        if needle in lowered:
            reasons.append(f"global_block:{needle}")

    if PAN_RE.search(answer):
        reasons.append("pan_echo_in_output")

    if case.get("expect_refusal"):
        # Refusal should not look like a clean factual success for advice/PII.
        if case.get("category") in {"advisory", "comparative", "pii", "mixed"}:
            if FOOTER_RE.search(answer) and "Source:" in answer:
                reasons.append("refusal_looks_factual")
    else:
        audit = audit_response(answer)
        if not audit.ok:
            reasons.append(f"audit_failed:{';'.join(audit.reasons)}")

        if case.get("must_match_footer") and not FOOTER_RE.search(answer):
            reasons.append("missing_footer")

        if case.get("require_single_source"):
            if len(URL_RE.findall(answer)) != 1:
                reasons.append(
                    f"source_count={len(URL_RE.findall(answer))}"
                )

        max_sent = case.get("max_body_sentences")
        if max_sent is not None:
            source_idx = answer.find("Source:")
            body = answer if source_idx < 0 else answer[:source_idx]
            sentences = [p for p in SENTENCE_SPLIT_RE.split(body.strip()) if p]
            if len(sentences) > int(max_sent):
                reasons.append(f"body_sentences={len(sentences)}")

    if case.get("category") == "performance":
        if "cagr" in lowered and "i calculate" in lowered:
            reasons.append("fabricated_return_calculation")

    return reasons


def main() -> int:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    settings = get_settings()

    passed = 0
    by_cat: dict[str, list[bool]] = defaultdict(list)

    for case in cases:
        case_id = case["id"]
        query = case["query"]
        category = case.get("category", "unknown")
        display_q = _redact_query(query)

        try:
            intent = classify(query, settings)
            answer = answer_query(query, settings)
            reasons = _check_case(case, answer, intent.value)
        except Exception as exc:  # noqa: BLE001 — eval must not crash mid-suite
            reasons = [f"exception:{type(exc).__name__}:{exc}"]

        ok = not reasons
        by_cat[category].append(ok)
        if ok:
            passed += 1
            print(f"PASS {case_id}")
        else:
            print(f"FAIL {case_id}  reasons={reasons}  query={display_q!r}")

    total = len(cases)
    print(f"\nSummary: {passed}/{total} passed")
    for cat, results in sorted(by_cat.items()):
        print(f"  {cat}: {sum(results)}/{len(results)}")

    if passed != total:
        print("EXIT 1")
        return 1
    print("EXIT 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
