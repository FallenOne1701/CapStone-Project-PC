from datetime import date, datetime, timezone

from src.audit import audit_pulse
from src.models import PulseDoc, Review


def _doc(**kwargs):
    base = dict(
        title="t",
        window_start=date(2026, 9, 8),
        window_end=date(2026, 11, 17),
        review_count=3,
        themes=["A", "B", "C"],
        quotes=["alpha beta", "gamma", "delta"],
        actions=["a1", "a2", "a3"],
        body_markdown="word " * 10,
        created_at=datetime.now(timezone.utc),
    )
    base.update(kwargs)
    return PulseDoc(**base)


def test_audit_passes_grounded_quotes():
    reviews = [
        Review(review_id="1", rating=1, text="alpha beta extra", created_at=date(2026, 10, 1)),
        Review(review_id="2", rating=1, text="gamma yes", created_at=date(2026, 10, 1)),
        Review(review_id="3", rating=1, text="delta ok", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(_doc(), reviews)
    assert result.ok


def test_audit_rejects_invented_quote():
    reviews = [
        Review(review_id="1", rating=1, text="only this text", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(
        _doc(quotes=["invented quote", "only this text", "only this text"]),
        reviews,
    )
    assert not result.ok
    assert any("quote" in e.lower() for e in result.errors)


def test_audit_rejects_pii_in_body():
    reviews = [
        Review(review_id="1", rating=1, text="hello world", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(
        _doc(
            quotes=["hello world", "hello world", "hello world"],
            body_markdown="reach me at x@y.com " + ("word " * 20),
        ),
        reviews,
    )
    assert not result.ok
