from datetime import date

from src.clean import clean_reviews, strip_pii_text
from src.models import Review


def test_strip_email_and_phone():
    raw = "Contact me at user@example.com or +91 98765 43210 about KYC"
    cleaned = strip_pii_text(raw)
    assert "user@example.com" not in cleaned
    assert "98765" not in cleaned
    assert "KYC" in cleaned


def test_clean_reviews_redacts_body():
    reviews = [
        Review(
            review_id="1",
            rating=2,
            text="Help email me at a@b.com",
            created_at=date(2026, 10, 1),
        )
    ]
    out = clean_reviews(reviews)
    assert "a@b.com" not in out[0].text
