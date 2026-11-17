from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import main
from src.config import Settings


SETTINGS = Settings(
    groq_api_key="test",
    chat_model="llama-3.3-70b-versatile",
    groq_base_url="https://api.groq.com/openai/v1",
    embed_model="BAAI/bge-small-en-v1.5",
    chroma_path=Path("corpus_index"),
    similarity_threshold=0.55,
    top_k=3,
)


def test_health():
    client = TestClient(main.app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_ask_factual_shape(monkeypatch):
    factual = (
        "Expense ratio is 0.90%.\n"
        "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
        "Last updated from sources: 2026-11-17"
    )
    monkeypatch.setattr(main, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(main, "answer_query", lambda q, s: factual)

    client = TestClient(main.app)
    res = client.post("/api/ask", json={"question": "expense ratio large cap?"})
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "factual"
    assert body["citation_url"].startswith("https://groww.in/")
    assert body["last_updated"] == "2026-11-17"


def test_ask_refusal_shape(monkeypatch):
    refusal = (
        "I can't provide investment advice or fund recommendations. "
        f"For investor education, see: {SETTINGS.educational_link}"
    )
    monkeypatch.setattr(main, "get_settings", lambda: SETTINGS)
    monkeypatch.setattr(main, "answer_query", lambda q, s: refusal)

    client = TestClient(main.app)
    res = client.post("/api/ask", json={"question": "Should I invest?"})
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "refusal"
    assert body["reason"] == "advisory"
    assert "educational_url" in body
