from pathlib import Path

from src.config import Settings
from src.rag.classify import Intent
from src.rag.retrieve import RetrievedChunk

SETTINGS = Settings(
    groq_api_key="x",
    chat_model="llama-3.3-70b-versatile",
    groq_base_url="https://api.groq.com/openai/v1",
    embed_model="BAAI/bge-small-en-v1.5",
    chroma_path=Path("."),
    similarity_threshold=0.55,
    top_k=3,
)

CHUNK = RetrievedChunk(
    text="HDFC Large Cap Fund - Direct Growth. Expense ratio\nExpense ratio is 0.80%.",
    source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    as_of_date="2025-11-17",
    scheme_id="hdfc-large-cap-fund-direct-growth",
    section="expense ratio",
    score=0.9,
)

GOOD_ANSWER = (
    "The Direct plan expense ratio is 0.80%.\n"
    "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
    "Last updated from sources: 2025-11-17"
)


def test_orchestrator_refuses_advisory(monkeypatch):
    from src.rag import orchestrator

    monkeypatch.setattr(
        orchestrator, "classify", lambda q, s=None: Intent.ADVISORY
    )
    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    out = orchestrator.answer_query("Should I buy this?")
    assert "https://www.amfiindia.com" in out


def test_orchestrator_pii_refuses_without_retrieve(monkeypatch):
    from src.rag import orchestrator

    called = {"retrieve": False}

    def fake_retrieve(*_a, **_k):
        called["retrieve"] = True
        return [CHUNK]

    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(orchestrator, "retrieve", fake_retrieve)
    out = orchestrator.answer_query("My PAN is ABCDE1234F, show holdings")
    assert called["retrieve"] is False
    assert "personal" in out.lower() or "identifier" in out.lower()
    assert "ABCDE1234F" not in out


def test_orchestrator_factual_path_audits_answer(monkeypatch):
    from src.rag import orchestrator

    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(
        orchestrator, "classify", lambda q, s=None: Intent.FACTUAL_SCHEME
    )
    monkeypatch.setattr(
        orchestrator, "detect_scheme_id", lambda q: "hdfc-large-cap-fund-direct-growth"
    )
    monkeypatch.setattr(orchestrator, "retrieve", lambda *_a, **_k: [CHUNK])
    monkeypatch.setattr(
        orchestrator, "answer_from_chunks", lambda *_a, **_k: GOOD_ANSWER
    )
    out = orchestrator.answer_query(
        "What is the expense ratio of HDFC Large Cap Fund?"
    )
    assert "Source: https://groww.in/" in out
    assert "Last updated from sources:" in out


def test_orchestrator_empty_retrieval_refuses(monkeypatch):
    from src.rag import orchestrator

    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(
        orchestrator, "classify", lambda q, s=None: Intent.FACTUAL_SCHEME
    )
    monkeypatch.setattr(
        orchestrator, "detect_scheme_id", lambda q: "hdfc-large-cap-fund-direct-growth"
    )
    monkeypatch.setattr(orchestrator, "retrieve", lambda *_a, **_k: [])
    out = orchestrator.answer_query(
        "What is the expense ratio of HDFC Large Cap Fund?"
    )
    assert "corpus" in out.lower() or "couldn't find" in out.lower() or "indexed" in out.lower()


def test_orchestrator_process_without_scheme_refuses(monkeypatch):
    from src.rag import orchestrator

    called = {"retrieve": False}

    def fake_retrieve(*_a, **_k):
        called["retrieve"] = True
        return [CHUNK]

    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(
        orchestrator, "classify", lambda q, s=None: Intent.FACTUAL_PROCESS
    )
    monkeypatch.setattr(orchestrator, "detect_scheme_id", lambda q: None)
    monkeypatch.setattr(orchestrator, "retrieve", fake_retrieve)
    out = orchestrator.answer_query(
        "How can I download my capital gains report for mutual funds?"
    )
    assert called["retrieve"] is False
    assert "Source:" not in out
    assert "Last updated from sources:" not in out


def test_orchestrator_retries_once_when_audit_fails(monkeypatch):
    from src.rag import orchestrator

    calls = {"n": 0}

    def fake_answer(query, chunks, settings, strict=False):
        calls["n"] += 1
        if calls["n"] == 1:
            return (
                "The expense ratio is 0.80%. I recommend buying this fund.\n"
                "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
                "Last updated from sources: 2025-11-17"
            )
        return GOOD_ANSWER

    monkeypatch.setattr(orchestrator, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(
        orchestrator, "classify", lambda q, s=None: Intent.FACTUAL_SCHEME
    )
    monkeypatch.setattr(
        orchestrator, "detect_scheme_id", lambda q: "hdfc-large-cap-fund-direct-growth"
    )
    monkeypatch.setattr(orchestrator, "retrieve", lambda *_a, **_k: [CHUNK])
    monkeypatch.setattr(orchestrator, "answer_from_chunks", fake_answer)
    out = orchestrator.answer_query(
        "What is the expense ratio of HDFC Large Cap Fund?"
    )
    assert calls["n"] == 2
    assert out == GOOD_ANSWER
