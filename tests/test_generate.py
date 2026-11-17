from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.rag.retrieve import RetrievedChunk


def _chunk() -> RetrievedChunk:
    return RetrievedChunk(
        text="HDFC Large Cap Fund - Direct Growth. Expense ratio\nExpense ratio is 0.80%.",
        source_url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        as_of_date="2025-11-17",
        scheme_id="hdfc-large-cap-fund-direct-growth",
        section="expense ratio",
        score=0.9,
    )


def test_system_factual_prompt_exists():
    path = Path("prompts/system_factual.txt")
    text = path.read_text(encoding="utf-8")
    assert "facts-only" in text.lower()
    assert "Do not invent numbers or URLs." in text


def test_generate_factual_answer_uses_groq_and_returns_body(monkeypatch):
    from src.rag import generate as generate_mod

    settings = MagicMock()
    settings.chat_model = "llama-3.3-70b-versatile"

    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = (
        "The Direct plan expense ratio is 0.80%."
    )

    client = MagicMock()
    client.chat.completions.create.return_value = response
    monkeypatch.setattr(generate_mod, "get_groq_client", lambda _s: client)

    body = generate_mod.generate_factual_answer(
        "What is the expense ratio of HDFC Large Cap Fund?",
        [_chunk()],
        settings,
    )

    assert body == "The Direct plan expense ratio is 0.80%."
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert kwargs["temperature"] == 0.0
    messages = kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "facts-only" in messages[0]["content"].lower()
    assert messages[1]["role"] == "user"
    assert "expense ratio is 0.80%" in messages[1]["content"].lower()
    assert "What is the expense ratio" in messages[1]["content"]


def test_answer_from_chunks_formats_citation_and_footer(monkeypatch):
    from src.rag import generate as generate_mod

    settings = MagicMock()
    monkeypatch.setattr(
        generate_mod,
        "generate_factual_answer",
        lambda *_a, **_k: "The Direct plan expense ratio is 0.80%.",
    )

    out = generate_mod.answer_from_chunks(
        "What is the expense ratio of HDFC Large Cap Fund?",
        [_chunk()],
        settings,
    )
    assert out.startswith("The Direct plan expense ratio is 0.80%.")
    assert "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth" in out
    assert "Last updated from sources: 2025-11-17" in out
