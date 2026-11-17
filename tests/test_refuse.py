from pathlib import Path

from src.config import Settings
from src.rag.classify import Intent
from src.rag.refuse import build_refusal

SETTINGS = Settings(
    groq_api_key="x",
    chat_model="llama-3.3-70b-versatile",
    groq_base_url="https://api.groq.com/openai/v1",
    embed_model="BAAI/bge-small-en-v1.5",
    chroma_path=Path("."),
    similarity_threshold=0.35,
    top_k=4,
)


def test_advisory_refusal_has_edu_link_and_no_advice():
    text = build_refusal(Intent.ADVISORY, None, SETTINGS)
    assert "investment advice" in text.lower() or "cannot" in text.lower()
    assert SETTINGS.educational_link in text
    assert "i recommend" not in text.lower()


def test_performance_points_to_groww_page_when_scheme_known():
    text = build_refusal(
        Intent.PERFORMANCE, "hdfc-large-cap-fund-direct-growth", SETTINGS
    )
    assert "groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth" in text


def test_comparative_refusal_includes_edu_link():
    text = build_refusal(Intent.COMPARATIVE, None, SETTINGS)
    assert SETTINGS.educational_link in text
    assert "compar" in text.lower() or "recommend" not in text.lower()


def test_pii_refusal_does_not_echo_identifiers():
    text = build_refusal(Intent.PII_SENSITIVE, None, SETTINGS)
    assert "pan" not in text.lower() or "do not" in text.lower() or "cannot" in text.lower()
    assert "ABCDE1234F" not in text
    assert SETTINGS.educational_link not in text
