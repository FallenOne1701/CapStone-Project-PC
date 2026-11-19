from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest


@dataclass
class _FakeRetrieve:
    chunks: list
    source_urls: list
    searched: list


def test_policy_refuses_advice_without_calling_draft(monkeypatch):
    from src.desk import draft_agent, policy_agent

    draft_spy = MagicMock(wraps=draft_agent.run_draft)
    monkeypatch.setattr(draft_agent, "run_draft", draft_spy)

    result = policy_agent.run_policy("Should I buy this mutual fund right now?")
    assert result.allow is False
    assert result.refuse is True
    assert any("advice" in r.lower() or "advisory" in r.lower() for r in result.reasons)
    draft_spy.assert_not_called()


def test_policy_refuses_pii_without_calling_draft(monkeypatch):
    from src.desk import draft_agent, policy_agent

    draft_spy = MagicMock(wraps=draft_agent.run_draft)
    monkeypatch.setattr(draft_agent, "run_draft", draft_spy)

    result = policy_agent.run_policy(
        "My PAN is ABCDE1234F and my phone is 9876543210 — check my folio"
    )
    assert result.allow is False
    assert result.refuse is True
    assert any("pii" in r.lower() for r in result.reasons)
    draft_spy.assert_not_called()


def test_policy_refuses_returns_performance():
    from src.desk.policy_agent import run_policy

    result = run_policy("What were the historical returns and CAGR of this fund?")
    assert result.refuse is True
    assert result.allow is False


def test_policy_allows_factual_question():
    from src.desk.policy_agent import run_policy

    result = run_policy("What is the exit load for Groww Nifty 50 index fund?")
    assert result.allow is True
    assert result.refuse is False


def test_retrieve_always_populates_searched(monkeypatch):
    from src.desk import faq_client, retrieve_agent

    monkeypatch.setattr(
        faq_client,
        "faq_retrieve",
        lambda q: faq_client.RetrieveResult(chunks=[], source_urls=[], searched=[]),
    )
    # Even if adapter returned empty searched, agent must ensure non-empty
    result = retrieve_agent.run_retrieve("unknown topic xyz")
    assert isinstance(result.searched, list)
    assert len(result.searched) > 0


def test_retrieve_uses_faq_client(monkeypatch):
    from src.desk import faq_client, retrieve_agent

    expected = faq_client.RetrieveResult(
        chunks=[{"text": "Exit load is 1%", "source_url": "https://groww.in/p/exit"}],
        source_urls=["https://groww.in/p/exit"],
        searched=["FAQ corpus", "https://groww.in/p/exit"],
    )
    monkeypatch.setattr(faq_client, "faq_retrieve", lambda q: expected)
    result = retrieve_agent.run_retrieve("exit load?")
    assert result.source_urls == expected.source_urls
    assert "FAQ corpus" in result.searched or len(result.searched) > 0


def test_draft_returns_short_text_from_retrieve():
    from src.desk.draft_agent import run_draft
    from src.desk.faq_client import RetrieveResult

    retrieve = RetrieveResult(
        chunks=[
            {
                "text": "Exit load is 1% if redeemed within 7 days.",
                "source_url": "https://groww.in/p/exit-load",
            }
        ],
        source_urls=["https://groww.in/p/exit-load"],
        searched=["FAQ corpus", "https://groww.in/p/exit-load"],
    )
    draft = run_draft("What is the exit load?", retrieve, fixture_mode=True)
    assert isinstance(draft, str)
    assert draft.strip()
    # ≤3 sentences (rough: at most 3 period-terminated clauses)
    sentences = [s for s in draft.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    assert len(sentences) <= 3
    assert "https://groww.in/p/exit-load" in draft or "not_covered" in draft.lower()


def test_draft_not_covered_when_no_chunks():
    from src.desk.draft_agent import run_draft
    from src.desk.faq_client import RetrieveResult

    retrieve = RetrieveResult(
        chunks=[],
        source_urls=[],
        searched=["FAQ corpus", "query:totally unknown"],
    )
    draft = run_draft("totally unknown topic", retrieve, fixture_mode=True)
    assert "not_covered" in draft.lower()


def test_agents_run_in_parallel(monkeypatch):
    import time

    from src.desk import draft_agent, policy_agent, retrieve_agent
    from src.desk.agents import run_agents_parallel
    from src.desk.faq_client import RetrieveResult

    def slow_policy(q):
        time.sleep(0.15)
        return policy_agent.PolicyResult(
            allow=True, refuse=False, reasons=["ok"], category="factual"
        )

    def slow_retrieve(q):
        time.sleep(0.15)
        return RetrieveResult(
            chunks=[{"text": "fact", "source_url": "https://groww.in/x"}],
            source_urls=["https://groww.in/x"],
            searched=["FAQ corpus"],
        )

    def slow_draft(q, retrieve, fixture_mode=None):
        time.sleep(0.15)
        return "Fact only. https://groww.in/x"

    monkeypatch.setattr(policy_agent, "run_policy", slow_policy)
    monkeypatch.setattr(retrieve_agent, "run_retrieve", slow_retrieve)
    monkeypatch.setattr(draft_agent, "run_draft", slow_draft)

    t0 = time.perf_counter()
    policy, retrieve, draft = run_agents_parallel(
        "What is exit load?", fixture_mode=True
    )
    elapsed = time.perf_counter() - t0

    assert policy.allow is True
    assert retrieve.searched
    assert draft
    # Sequential would be ~0.45s; parallel should be well under that
    assert elapsed < 0.40
