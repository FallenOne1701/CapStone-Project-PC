from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.desk import draft_agent
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import run_policy

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SEEDS_PATH = PACKAGE_ROOT / "data" / "seeds" / "questions.jsonl"
CLAIMS_CHECKLIST_PATH = (
    PACKAGE_ROOT / "data" / "fixtures" / "eval_claims_checklist.json"
)

GROUNDED_URL = "https://groww.in/p/exit-load"
OFFICIAL_URLS = (
    "https://groww.in/p/exit-load",
    "https://groww.in/p/brokerage-charges",
    "https://groww.in/p/mutual-funds",
)


def load_seeds(path: Path | None = None) -> list[dict[str, Any]]:
    seed_path = path or SEEDS_PATH
    rows: list[dict[str, Any]] = []
    for line in seed_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def grounded_retrieve(question: str) -> RetrieveResult:
    return RetrieveResult(
        chunks=[
            {
                "text": "Exit load is 1% if redeemed within 7 days on many Groww MF schemes.",
                "source_url": GROUNDED_URL,
            }
        ],
        source_urls=[GROUNDED_URL],
        searched=["FAQ corpus", GROUNDED_URL, f"query:{question[:80]}"],
    )


def empty_retrieve(question: str) -> RetrieveResult:
    return RetrieveResult(
        chunks=[],
        source_urls=[],
        searched=["FAQ corpus", f"query:{question[:80]}"],
    )


def seed_by_question(
    seeds: list[dict[str, Any]], question: str
) -> dict[str, Any] | None:
    from src.pii import redact_pii

    for row in seeds:
        raw = str(row.get("question") or "")
        if raw == question or redact_pii(raw) == question:
            return row
    return None


def agents_for_eval(seeds: list[dict[str, Any]]):
    """Return a run_agents_parallel stand-in: real policy + fixture draft/retrieve."""

    def _run(question: str, fixture_mode: bool | None = None):
        policy = run_policy(question)
        seed = seed_by_question(seeds, question)
        tags = set(seed.get("tags") or []) if seed else set()
        if "oos" in tags:
            retrieve = empty_retrieve(question)
        else:
            retrieve = grounded_retrieve(question)
        draft = draft_agent._fixture_draft(question, retrieve)
        return policy, retrieve, draft

    return _run
