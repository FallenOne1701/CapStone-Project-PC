from __future__ import annotations

import io
import json
import logging
from datetime import date

from src.db import init_db
from src.models import QueueStatus
from src.pii import contains_pii, redact_pii
from tests.eval_helpers import (
    CLAIMS_CHECKLIST_PATH,
    OFFICIAL_URLS,
    agents_for_eval,
    load_seeds,
)


def test_claims_checklist_has_at_least_15_sourced_rows():
    raw = json.loads(CLAIMS_CHECKLIST_PATH.read_text(encoding="utf-8"))
    claims = raw["claims"]
    assert len(claims) >= int(raw.get("min_claims") or 15)
    for row in claims:
        assert row.get("id") is not None
        assert row.get("loop") in {"support", "product"}
        assert (row.get("claim") or "").strip()
        source = (row.get("source") or "").strip()
        assert source, f"claim {row.get('id')} missing source"
        # Source must be URL, review id, policy/pii marker, FAQ corpus, or window tag
        ok_prefix = (
            source.startswith("http"),
            source.startswith("review:"),
            source.startswith("policy:"),
            source.startswith("pii:"),
            source.startswith("window:"),
            source == "FAQ corpus",
        )
        assert any(ok_prefix), f"claim {row.get('id')} bad source {source!r}"


def test_oos_advice_returns_refused_or_not_covered(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    seeds = load_seeds()
    db = tmp_path / "grounding.db"
    init_db(db)
    monkeypatch.setattr(agents, "run_agents_parallel", agents_for_eval(seeds))

    for seed in seeds:
        tags = set(seed.get("tags") or [])
        if not tags.intersection({"oos", "advisory", "returns"}):
            continue
        item = pipeline.process_question(
            seed["question"], db_path=db, fixture_mode=True
        )
        assert item.status == QueueStatus.not_covered, seed["id"]
        assert item.searched, seed["id"]
        draft_l = (item.draft or "").lower()
        assert "you should buy" not in draft_l
        assert "i recommend" not in draft_l
        if "oos" in tags:
            assert item.routing_note == "not_covered"
            assert any("FAQ" in s or "query:" in s for s in item.searched)
        if "advisory" in tags:
            assert item.agent_package.get("policy", {}).get("refuse") is True
            assert item.agent_package.get("policy", {}).get("category") == "advice"
        if "returns" in tags:
            assert item.agent_package.get("policy", {}).get("refuse") is True
            assert item.agent_package.get("policy", {}).get("category") == "returns"
            for banned in ("12%", "15%", "cagr was"):
                assert banned not in draft_l


def test_pii_redacted_and_absent_from_log_sink(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    seeds = [s for s in load_seeds() if "pii" in (s.get("tags") or [])]
    assert len(seeds) >= 3

    db = tmp_path / "pii_eval.db"
    init_db(db)
    monkeypatch.setattr(agents, "run_agents_parallel", agents_for_eval(load_seeds()))

    log_buf = io.StringIO()
    handler = logging.StreamHandler(log_buf)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    prev_level = root.level
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    try:
        for seed in seeds:
            raw_tokens = seed.get("must_not_include") or []
            assert raw_tokens, seed["id"]
            for token in raw_tokens:
                assert contains_pii(seed["question"]) or token in seed["question"]

            item = pipeline.process_question(
                seed["question"], db_path=db, fixture_mode=True
            )
            blob = "\n".join(
                [
                    item.question_text,
                    item.draft or "",
                    json.dumps(item.agent_package),
                    json.dumps(item.searched),
                ]
            )
            for token in raw_tokens:
                assert token not in blob, f"{seed['id']} leaked {token} into state"
                assert token not in redact_pii(seed["question"])
            assert item.status in {QueueStatus.drafted, QueueStatus.not_covered}
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)

    log_text = log_buf.getvalue()
    for seed in seeds:
        for token in seed.get("must_not_include") or []:
            assert token not in log_text, f"log sink leaked {token}"


def test_drafted_factual_claims_use_allowlisted_citation(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    seeds = load_seeds()
    db = tmp_path / "cite.db"
    init_db(db)
    monkeypatch.setattr(agents, "run_agents_parallel", agents_for_eval(seeds))

    drafted = 0
    for seed in seeds:
        if "factual" not in (seed.get("tags") or []) and "process" not in (
            seed.get("tags") or []
        ):
            continue
        item = pipeline.process_question(
            seed["question"], db_path=db, fixture_mode=True
        )
        if item.status != QueueStatus.drafted:
            continue
        drafted += 1
        assert item.citation_url in OFFICIAL_URLS, seed["id"]
        assert item.citation_url in (item.draft or "")
    assert drafted >= 5


def test_fee_explainer_links_are_official():
    from src.models import FeeExplainer

    explainer = FeeExplainer(
        bullets=["Exit load may apply", "Check scheme document", "Charges vary by scheme"],
        links=[
            "https://groww.in/p/brokerage-charges",
            "https://groww.in/p/mutual-funds",
        ],
        last_checked=date(2026, 11, 19),
    )
    for link in explainer.links:
        assert link.startswith("https://groww.in/")
