from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.desk.draft_agent import _sentence_cap
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.models import QueueStatus

_URL_RE = re.compile(r"https?://[^\s\]\)>\"']+")


@dataclass
class CandidateReply:
    status: QueueStatus
    draft: str | None
    citation_url: str | None
    routing_note: str
    searched: list[str] = field(default_factory=list)
    policy_category: str = "factual"


def _pick_citation(draft: str, retrieve: RetrieveResult) -> str | None:
    allow = set(retrieve.source_urls)
    for chunk in retrieve.chunks:
        url = str(chunk.get("source_url") or "").strip()
        if url:
            allow.add(url)
    # Prefer allowlisted URL appearing in draft
    for match in _URL_RE.findall(draft or ""):
        if match in allow:
            return match
    if retrieve.source_urls:
        return retrieve.source_urls[0]
    return None


def _refuse_stub(policy: PolicyResult, searched: list[str]) -> str:
    searched_note = ", ".join(searched) if searched else "FAQ corpus"
    if policy.category == "pii":
        return (
            "not_covered: this question appears to include personal data. "
            f"Searched: {searched_note}."
        )
    if policy.category in {"advice", "returns"}:
        return (
            "not_covered: I can't provide investment advice, buy/sell guidance, "
            f"or return/performance figures. Searched: {searched_note}."
        )
    return f"not_covered: refused by policy. Searched: {searched_note}."


def orchestrate(
    policy: PolicyResult,
    retrieve: RetrieveResult,
    draft: str,
) -> CandidateReply:
    """Merge parallel agent outputs into a candidate queue item payload."""
    searched = list(retrieve.searched) if retrieve.searched else ["FAQ corpus"]

    if policy.refuse:
        routing = (
            "escalate_human" if policy.category in {"advice", "pii"} else "not_covered"
        )
        return CandidateReply(
            status=QueueStatus.not_covered,
            draft=_refuse_stub(policy, searched),
            citation_url=None,
            routing_note=routing,
            searched=searched,
            policy_category=policy.category,
        )

    text = (draft or "").strip()
    lower = text.lower()
    has_not_covered = "not_covered" in lower
    has_chunks = bool(retrieve.chunks) or bool(retrieve.source_urls)
    citation = _pick_citation(text, retrieve) if has_chunks else None

    if has_not_covered or not has_chunks or not citation:
        return CandidateReply(
            status=QueueStatus.not_covered,
            draft=text or _refuse_stub(policy, searched),
            citation_url=None,
            routing_note="not_covered",
            searched=searched,
            policy_category=policy.category,
        )

    capped = _sentence_cap(text, max_sentences=3)
    return CandidateReply(
        status=QueueStatus.drafted,
        draft=capped,
        citation_url=citation,
        routing_note="answer",
        searched=searched,
        policy_category=policy.category,
    )
