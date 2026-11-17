from pathlib import Path

from src.api.respond import map_answer_to_response
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


def test_map_factual_answer():
    text = (
        "The exit load is 1% if redeemed within 1 year.\n"
        "Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n"
        "Last updated from sources: 2026-11-17"
    )
    out = map_answer_to_response(text, SETTINGS)
    assert out["type"] == "factual"
    assert "exit load" in out["answer"].lower()
    assert out["citation_url"].startswith("https://groww.in/")
    assert out["last_updated"] == "2026-11-17"
    assert out["scheme_id"] == "hdfc-mid-cap-fund-direct-growth"


def test_map_refusal_answer():
    text = (
        "I can't provide investment advice or fund recommendations. "
        f"For investor education, see: {SETTINGS.educational_link}"
    )
    out = map_answer_to_response(text, SETTINGS)
    assert out["type"] == "refusal"
    assert out["reason"] == "advisory"
    assert "amfiindia.com" in out["educational_url"]
