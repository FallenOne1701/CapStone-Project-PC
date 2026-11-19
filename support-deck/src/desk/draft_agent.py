from __future__ import annotations

import re

from src.config import PACKAGE_ROOT, get_settings
from src.desk.faq_client import RetrieveResult

_PROMPT_PATH = PACKAGE_ROOT / "prompts" / "draft_system.txt"

# Split only on .!? followed by whitespace (or end) — does not break URLs.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _sentence_cap(text: str, max_sentences: int = 3) -> str:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    return " ".join(parts[:max_sentences]).strip()


def _fixture_draft(q: str, retrieve: RetrieveResult) -> str:
    if not retrieve.chunks and not retrieve.source_urls:
        searched = ", ".join(retrieve.searched) if retrieve.searched else "FAQ corpus"
        return (
            f"not_covered: no grounded passage found for this question. "
            f"Searched: {searched}."
        )
    chunk = retrieve.chunks[0] if retrieve.chunks else {}
    fact = str(chunk.get("text") or "").strip() or "Official FAQ notes apply."
    # Keep fixture draft to one short sentence + citation
    citation = (
        retrieve.source_urls[0]
        if retrieve.source_urls
        else str(chunk.get("source_url") or "")
    )
    body = fact
    if len(body) > 180:
        body = body[:177].rstrip() + "..."
    if citation:
        return _sentence_cap(f"{body} Source: {citation}")
    return _sentence_cap(
        f"{body} not_covered: citation URL missing from retrieve context."
    )


def _groq_draft(q: str, retrieve: RetrieveResult) -> str:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_groq import ChatGroq
    from pydantic import BaseModel, Field

    class _DraftOut(BaseModel):
        draft: str = Field(description="≤3 factual sentences or not_covered stub")

    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY missing for draft agent")

    system = _PROMPT_PATH.read_text(encoding="utf-8").strip()
    ctx_lines: list[str] = []
    for i, chunk in enumerate(retrieve.chunks[:5], start=1):
        url = chunk.get("source_url") or ""
        ctx_lines.append(f"[{i}] {chunk.get('text', '')}\nURL: {url}")
    context = "\n\n".join(ctx_lines) if ctx_lines else "(no passages)"
    urls = ", ".join(retrieve.source_urls) or "(none)"
    searched = ", ".join(retrieve.searched) or "FAQ corpus"

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_chat_model,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (
                "human",
                "Question: {question}\n\nPassages:\n{context}\n\n"
                "Allowed citation URLs: {urls}\nSearched: {searched}\n"
                "Reply with ≤3 sentences and exactly one citation URL, "
                "or a not_covered message naming what was searched.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(_DraftOut)
    payload: _DraftOut = chain.invoke(
        {
            "question": q,
            "context": context,
            "urls": urls,
            "searched": searched,
        }
    )
    return _sentence_cap(payload.draft)


def run_draft(
    q: str,
    retrieve: RetrieveResult,
    *,
    fixture_mode: bool | None = None,
) -> str:
    """Propose ≤3-sentence facts-only reply from retrieve context.

    ``fixture_mode=True`` skips Groq (unit tests). When None, fixture mode
    is used automatically if ``GROQ_API_KEY`` is empty.
    """
    settings = get_settings()
    use_fixture = (
        True
        if fixture_mode is True
        else False
        if fixture_mode is False
        else not bool(settings.groq_api_key)
    )
    if use_fixture:
        return _fixture_draft(q, retrieve)
    return _groq_draft(q, retrieve)
