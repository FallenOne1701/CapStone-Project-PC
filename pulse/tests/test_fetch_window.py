from datetime import date

from src.fetch_play import filter_by_window, window_bounds
from src.models import Review


def test_window_bounds_ten_weeks():
    start, end = window_bounds(10, today=date(2026, 11, 17))
    assert end == date(2026, 11, 17)
    assert (end - start).days == 70


def test_filter_by_window_drops_old():
    reviews = [
        Review(
            review_id="1",
            rating=5,
            text="new enough",
            created_at=date(2026, 10, 1),
        ),
        Review(
            review_id="2",
            rating=1,
            text="too old",
            created_at=date(2026, 1, 1),
        ),
    ]
    start, end = window_bounds(10, today=date(2026, 11, 17))
    kept = filter_by_window(reviews, start, end)
    assert [r.review_id for r in kept] == ["1"]
