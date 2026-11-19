"""Fee/charge intent → canonical explainer reuse in the response loop.

When an active explainer exists and the question looks fee-related, the desk
skips retrieve/draft agents and answers from the explainer bullets (≤3
sentences) with ``routing_note=reuse_explainer``.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src.config import get_settings
from src.db import connect, init_db
from src.desk.draft_agent import _sentence_cap
from src.models import FeeExplainer
from src.weekly.fee_detect import _FEE_CUES


def _db_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(get_settings().support_deck_db)


def has_fee_intent(question: str) -> bool:
    """True when the question text matches fee/charge cues."""
    lower = (question or "").lower()
    return any(cue in lower for cue in _FEE_CUES)


def list_active_explainers(db_path: str | Path | None = None) -> list[FeeExplainer]:
    """Active explainers, newest ``updated_at`` first."""
    path = _db_path(db_path)
    init_db(path)
    con = connect(path)
    try:
        rows = con.execute(
            """
            SELECT * FROM explainers
            WHERE active = 1
            ORDER BY updated_at DESC, explainer_id ASC
            """
        ).fetchall()
    finally:
        con.close()
    out: list[FeeExplainer] = []
    for row in rows:
        out.append(
            FeeExplainer(
                explainer_id=row["explainer_id"],
                bullets=json.loads(row["bullets_json"]),
                links=json.loads(row["links_json"]),
                last_checked=date.fromisoformat(row["last_checked"]),
                active=bool(row["active"]),
            )
        )
    return out


def match_explainer(
    question: str,
    *,
    db_path: str | Path | None = None,
) -> FeeExplainer | None:
    """Return the canonical active explainer when the question is fee-intent."""
    if not has_fee_intent(question):
        return None
    active = list_active_explainers(db_path)
    if not active:
        return None
    return active[0]


def draft_from_explainer(explainer: FeeExplainer) -> str:
    """Build a ≤3-sentence reply from explainer bullets + primary citation."""
    bullets = [b.strip() for b in explainer.bullets if b and b.strip()]
    citation = explainer.links[0] if explainer.links else ""
    # Prefer up to two short bullet facts, then citation as its own sentence.
    facts = bullets[:2]
    if not facts:
        body = "Official fee and charge details are published on Groww."
    else:
        body = " ".join(
            f if f.endswith((".", "!", "?")) else f"{f}." for f in facts
        )
    # No trailing period after the URL — reviewer URL match is exact and
    # would treat ``…charges.`` as a different (ungrounded) citation.
    if citation:
        body = f"{body} Source: {citation}"
    return _sentence_cap(body, max_sentences=3)
