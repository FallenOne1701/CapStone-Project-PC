from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.desk.draft_agent import _SENTENCE_SPLIT
from src.desk.faq_client import RetrieveResult
from src.desk.orchestrator import CandidateReply
from src.models import QueueStatus
from src.pii import contains_pii

_URL_RE = re.compile(r"https?://[^\s\]\)>\"']+")


@dataclass
class ReviewResult:
    candidate: CandidateReply
    flags: list[str] = field(default_factory=list)
    passed: bool = True


def _sentence_count(text: str) -> int:
    parts = [p for p in _SENTENCE_SPLIT.split((text or "").strip()) if p.strip()]
    return len(parts)


def review(candidate: CandidateReply, retrieve: RetrieveResult) -> ReviewResult:
    """Check caps, citation, PII, grounding; may force not_covered if ungrounded."""
    flags: list[str] = []
    out = CandidateReply(
        status=candidate.status,
        draft=candidate.draft,
        citation_url=candidate.citation_url,
        routing_note=candidate.routing_note,
        searched=list(candidate.searched),
        policy_category=candidate.policy_category,
    )

    draft = out.draft or ""

    if draft and _sentence_count(draft) > 3:
        flags.append("cap_exceeded_sentences")

    if draft and contains_pii(draft):
        flags.append("pii_in_draft")

    allow = set(retrieve.source_urls)
    for chunk in retrieve.chunks:
        url = str(chunk.get("source_url") or "").strip()
        if url:
            allow.add(url)

    urls_in_draft = _URL_RE.findall(draft)
    if out.status == QueueStatus.drafted:
        if not out.citation_url:
            flags.append("missing_citation")
        elif out.citation_url not in allow:
            flags.append("ungrounded_citation")
        for url in urls_in_draft:
            if url not in allow:
                flags.append("ungrounded_citation")
                break

    # Policy-allowed path that still produced a draft with disallowed URL
    if out.status != QueueStatus.not_covered:
        for url in urls_in_draft:
            if allow and url not in allow:
                flags.append("ungrounded_citation")
                break
        if not allow and urls_in_draft:
            flags.append("ungrounded_citation")

    # Force not_covered when grounding/PII/cap critical
    force = any(
        f in flags
        for f in ("ungrounded_citation", "missing_citation", "pii_in_draft")
    )
    if force:
        out.status = QueueStatus.not_covered
        out.routing_note = "not_covered"
        out.citation_url = None
        if "ungrounded" in " ".join(flags) or "missing_citation" in flags:
            searched_note = ", ".join(out.searched) if out.searched else "FAQ corpus"
            out.draft = (
                f"not_covered: reply failed grounding review. Searched: {searched_note}."
            )
        elif "pii_in_draft" in flags:
            out.draft = "not_covered: draft contained personal data and was blocked."

    passed = out.status == QueueStatus.drafted and not flags
    # Cap alone is a soft flag (still drafted) unless combined with force reasons
    if "cap_exceeded_sentences" in flags and out.status == QueueStatus.drafted:
        passed = False

    return ReviewResult(candidate=out, flags=sorted(set(flags)), passed=passed)
