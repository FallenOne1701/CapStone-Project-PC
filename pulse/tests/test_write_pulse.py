from datetime import date, datetime, timezone

from src.models import PulseDoc, Review, Theme, ThemeResult
from src.write_pulse import count_words, render_pulse_markdown, select_quote_candidates


def test_select_quote_candidates_are_verbatim():
    reviews = [
        Review(
            review_id="1",
            rating=1,
            text="KYC keeps failing after uploading documents",
            created_at=date(2026, 10, 1),
            theme_id="kyc",
        )
    ]
    themes = ThemeResult(
        themes=[Theme(theme_id="kyc", label="KYC", review_ids=["1"], count=1)],
        top_theme_ids=["kyc"],
    )
    quotes = select_quote_candidates(reviews, themes)
    assert quotes[0] in reviews[0].text


def test_render_contains_sections():
    doc = PulseDoc(
        title="Groww Weekly Review Pulse — 2026-11-17",
        window_start=date(2026, 9, 8),
        window_end=date(2026, 11, 17),
        review_count=6,
        themes=["KYC", "Payments", "Stability"],
        quotes=["q1", "q2", "q3"],
        actions=["a1", "a2", "a3"],
        body_markdown="",
        created_at=datetime.now(timezone.utc),
    )
    md = render_pulse_markdown(doc)
    assert "## Top themes" in md
    assert "## What users said" in md
    assert "## Action ideas" in md
    assert count_words("one two three") == 3
