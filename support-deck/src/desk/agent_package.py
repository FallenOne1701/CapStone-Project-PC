from __future__ import annotations

from typing import Any, Literal

from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.desk.reviewer import ReviewResult
from src.models import FrequencyBucket


def _word_count(text: str | None) -> int:
    t = (text or "").strip()
    return len(t.split()) if t else 0


def build_agent_package(
    *,
    retrieve: RetrieveResult,
    policy: PolicyResult,
    reviewed: ReviewResult,
    bucket: FrequencyBucket,
    retrieve_path: Literal["faq", "reuse_explainer"],
    agents_fired_base: list[str],
    frequency_threshold: int,
    window_days: int = 7,
) -> dict[str, Any]:
    final = reviewed.candidate
    draft_text = final.draft or ""
    count = int(bucket.count)
    fired = list(agents_fired_base)
    if "pattern" not in fired:
        fired.append("pattern")
    return {
        "retrieve": {
            "path": retrieve_path,
            "chunk_count": len(retrieve.chunks),
            "source_urls": list(retrieve.source_urls),
            "searched": list(retrieve.searched),
        },
        "draft": {"text": draft_text, "word_count": _word_count(draft_text)},
        "policy": {
            "refuse": bool(policy.refuse),
            "allow": bool(policy.allow),
            "category": policy.category,
            "reasons": list(policy.reasons),
        },
        "pattern": {
            "normalized_text": bucket.normalized_text,
            "count": count,
            "window_days": window_days,
            "threshold": frequency_threshold,
            "recurring": count >= frequency_threshold,
            "window_start": bucket.window_start.isoformat(sep=" ")
            if bucket.window_start
            else None,
            "window_end": bucket.window_end.isoformat(sep=" ")
            if bucket.window_end
            else None,
        },
        "orchestrator": {
            "routing_note": final.routing_note,
            "status": final.status.value
            if hasattr(final.status, "value")
            else str(final.status),
            "citation_url": final.citation_url,
        },
        "reviewer": {
            "passed": bool(reviewed.passed),
            "flags": list(reviewed.flags),
            "round": 1,
        },
        "agents_fired": fired,
    }
