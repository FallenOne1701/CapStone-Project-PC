from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class _FakeChunk:
    text: str
    source_url: str
    as_of_date: str = "2026-01-01"
    scheme_id: str = "x"
    section: str = "exit load"
    score: float = 0.9


def test_faq_retrieve_searched_nonempty_on_empty_hits(monkeypatch):
    from src.desk import faq_client

    monkeypatch.setattr(
        faq_client,
        "_backend_retrieve",
        lambda question: ([], None, None),
    )
    result = faq_client.faq_retrieve("totally unknown topic xyz")
    assert result.chunks == []
    assert result.source_urls == []
    assert isinstance(result.searched, list)
    assert len(result.searched) > 0


def test_faq_retrieve_maps_chunks_and_urls(monkeypatch):
    from src.desk import faq_client

    chunk = _FakeChunk(
        text="Exit load is 1%",
        source_url="https://groww.in/example",
    )
    monkeypatch.setattr(
        faq_client,
        "_backend_retrieve",
        lambda question: ([chunk], "scheme-a", "exit load"),
    )
    result = faq_client.faq_retrieve("exit load?")
    assert result.chunks
    assert "https://groww.in/example" in result.source_urls
    assert "exit load" in " ".join(result.searched).lower() or any(
        "exit load" in s.lower() for s in result.searched
    )


def test_faq_classify_returns_intent_string(monkeypatch):
    from src.desk import faq_client

    class _Intent:
        value = "ADVISORY"

    monkeypatch.setattr(
        faq_client,
        "_backend_classify",
        lambda question: _Intent(),
    )
    assert faq_client.faq_classify("Should I buy this SIP?") == "ADVISORY"
