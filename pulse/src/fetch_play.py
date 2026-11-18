from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path

from google_play_scraper import Sort, reviews as play_reviews

from src.config import Settings
from src.models import Review


def window_bounds(weeks: int, today: date | None = None) -> tuple[date, date]:
    if weeks < 8 or weeks > 12:
        raise ValueError("lookback weeks must be between 8 and 12")
    end = today or date.today()
    start = end - timedelta(days=weeks * 7)
    return start, end


def filter_by_window(
    reviews: list[Review], start: date, end: date
) -> list[Review]:
    return [r for r in reviews if start <= r.created_at <= end]


def _to_review(raw: dict, app_id: str) -> Review | None:
    text = (raw.get("content") or "").strip()
    if not text:
        return None
    # Never copy userName into Review
    at = raw.get("at")
    if isinstance(at, datetime):
        created = at.date()
    else:
        created = date.today()
    return Review(
        review_id=str(raw.get("reviewId") or raw.get("review_id")),
        app_id=app_id,
        rating=int(raw.get("score") or raw.get("rating") or 0),
        title=(raw.get("title") or None),
        text=text,
        created_at=created,
        lang=None,
    )


def fetch_play_reviews(settings: Settings) -> list[Review]:
    """Fetch public Play reviews; stop early when older than window."""
    start, end = window_bounds(settings.pulse_lookback_weeks)
    collected: list[Review] = []
    token = None
    while len(collected) < settings.pulse_max_reviews:
        batch, token = play_reviews(
            settings.pulse_app_id,
            lang=settings.pulse_lang,
            country=settings.pulse_country,
            sort=Sort.NEWEST,
            count=100,
            continuation_token=token,
        )
        if not batch:
            break
        oldest_in_batch = end
        for raw in batch:
            rev = _to_review(raw, settings.pulse_app_id)
            if rev is None:
                continue
            oldest_in_batch = min(oldest_in_batch, rev.created_at)
            if start <= rev.created_at <= end:
                collected.append(rev)
        if oldest_in_batch < start or token is None:
            break
        time.sleep(0.5)
    return collected[: settings.pulse_max_reviews]


def save_raw_jsonl(reviews: list[Review], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in reviews:
            f.write(r.model_dump_json() + "\n")


def load_reviews_jsonl(path: Path) -> list[Review]:
    out: list[Review] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Review.model_validate_json(line))
    return out
