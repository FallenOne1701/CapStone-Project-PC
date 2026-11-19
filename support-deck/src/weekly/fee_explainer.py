from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from pydantic import BaseModel, Field

from src.config import PACKAGE_ROOT, get_settings
from src.db import connect
from src.models import FeeExplainer

_PROMPT_PATH = PACKAGE_ROOT / "prompts" / "fee_explainer_system.txt"


class _LLMFeeExplainer(BaseModel):
    bullets: list[str] = Field(default_factory=list, max_length=6)
    links: list[str] = Field(min_length=2, max_length=2)


def _normalize_links(sources: list[str]) -> list[str]:
    links = [s.strip() for s in sources if s and s.strip()]
    if len(links) < 2:
        raise ValueError("generate_fee_explainer requires at least 2 source URLs")
    return links[:2]


def _fixture_explainer(question_hint: str, links: list[str]) -> FeeExplainer:
    hint = (question_hint or "fees").strip() or "fees"
    bullets = [
        f"Groww publishes official fee and charge details for: {hint}.",
        "Fee figures depend on product type (e.g. stocks vs mutual funds) and the order path.",
        "Always verify the two official links below; this explainer is facts-only.",
    ]
    return FeeExplainer(
        explainer_id=f"fee-{uuid.uuid4().hex[:12]}",
        bullets=bullets,
        links=links,
        last_checked=date.today(),
        active=True,
    )


def _groq_explainer(question_hint: str, links: list[str]) -> FeeExplainer:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_groq import ChatGroq

    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY missing for fee explainer generation")

    system = _PROMPT_PATH.read_text(encoding="utf-8").strip()
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
                "Question hint: {hint}\nAllowed official links (use exactly these two):\n"
                "1. {link1}\n2. {link2}\n"
                "Return bullets (≤6) and the same two links. Facts only.",
            ),
        ]
    )
    chain = prompt | llm.with_structured_output(_LLMFeeExplainer)
    payload: _LLMFeeExplainer = chain.invoke(
        {"hint": question_hint, "link1": links[0], "link2": links[1]}
    )
    return FeeExplainer(
        explainer_id=f"fee-{uuid.uuid4().hex[:12]}",
        bullets=list(payload.bullets)[:6],
        links=links,
        last_checked=date.today(),
        active=True,
    )


def generate_fee_explainer(
    question_hint: str,
    sources: list[str],
    *,
    fixture_mode: bool | None = None,
) -> FeeExplainer:
    """Generate a canonical fee explainer.

    ``fixture_mode=True`` skips Groq (unit tests). When ``fixture_mode`` is
    None, fixture mode is used automatically if ``GROQ_API_KEY`` is empty.
    """
    links = _normalize_links(sources)
    settings = get_settings()
    use_fixture = (
        True
        if fixture_mode is True
        else False
        if fixture_mode is False
        else not bool(settings.groq_api_key)
    )
    if use_fixture:
        return _fixture_explainer(question_hint, links)
    return _groq_explainer(question_hint, links)


def upsert_explainer(db_path: str | Path, explainer: FeeExplainer) -> FeeExplainer:
    """Insert or update a row in ``explainers``; returns explainer with id set."""
    eid = explainer.explainer_id or f"fee-{uuid.uuid4().hex[:12]}"
    payload = explainer.model_copy(update={"explainer_id": eid})
    con = connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO explainers (
                explainer_id, bullets_json, links_json, last_checked, active, updated_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(explainer_id) DO UPDATE SET
                bullets_json = excluded.bullets_json,
                links_json = excluded.links_json,
                last_checked = excluded.last_checked,
                active = excluded.active,
                updated_at = datetime('now')
            """,
            (
                payload.explainer_id,
                json.dumps(payload.bullets),
                json.dumps(payload.links),
                payload.last_checked.isoformat(),
                1 if payload.active else 0,
            ),
        )
        con.commit()
    finally:
        con.close()
    return payload


def load_explainer(db_path: str | Path, explainer_id: str) -> FeeExplainer | None:
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT * FROM explainers WHERE explainer_id = ?",
            (explainer_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return FeeExplainer(
        explainer_id=row["explainer_id"],
        bullets=json.loads(row["bullets_json"]),
        links=json.loads(row["links_json"]),
        last_checked=date.fromisoformat(row["last_checked"]),
        active=bool(row["active"]),
    )
