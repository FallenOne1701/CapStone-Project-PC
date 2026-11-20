"""Queue-question frequency → weekly pulse signals.

Normalization is deterministic and local (no embeddings):

- redact PII, lowercase, strip punctuation
- drop a small stopword list (what/is/the/how/…)
- keep remaining token order

Limits: no synonym map (``fees`` stays distinct from ``charges``) and no
reordering, so only light paraphrases of the same words share a bucket.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import get_settings
from src.db import connect, init_db
from src.models import FrequencyBucket, FrequencySignal
from src.pii import redact_pii

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "what",
        "whats",
        "how",
        "do",
        "does",
        "did",
        "i",
        "my",
        "me",
        "you",
        "your",
        "please",
        "can",
        "could",
        "to",
        "of",
        "for",
        "on",
        "in",
        "and",
        "or",
    }
)


def _naive_utc(at: datetime) -> datetime:
    if at.tzinfo is None:
        return at
    return at.astimezone(timezone.utc).replace(tzinfo=None)


def _db_path(db_path: str | Path | None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(get_settings().support_deck_db)


def normalize_question(text: str) -> str:
    redacted = redact_pii(text or "")
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in redacted)
    tokens = [tok for tok in cleaned.split() if tok not in _STOPWORDS]
    return " ".join(tokens)


def _bucket_id(normalized: str) -> str:
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"fb-{digest}"


def _row_to_bucket(row: sqlite3.Row) -> FrequencyBucket:
    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value)

    return FrequencyBucket(
        bucket_id=row["bucket_id"],
        normalized_text=row["normalized_text"],
        count=int(row["count"]),
        window_start=_parse(row["window_start"]),
        window_end=_parse(row["window_end"]),
    )


def record_question(
    text: str,
    at: datetime,
    *,
    db_path: str | Path | None = None,
) -> FrequencyBucket:
    """Count one seen question. Stored text is normalized and PII-redacted."""
    path = _db_path(db_path)
    init_db(path)
    normalized = normalize_question(text)
    seen = _naive_utc(at)
    stamp = seen.isoformat(sep=" ")
    bucket_id = _bucket_id(normalized)

    con = connect(path)
    try:
        con.execute(
            """
            INSERT INTO frequency_buckets (
                bucket_id, normalized_text, count, window_start, window_end, updated_at
            ) VALUES (?, ?, 1, ?, ?, ?)
            ON CONFLICT(normalized_text) DO UPDATE SET
                count = frequency_buckets.count + 1,
                window_start = CASE
                    WHEN excluded.window_start < frequency_buckets.window_start
                    THEN excluded.window_start
                    ELSE frequency_buckets.window_start
                END,
                window_end = CASE
                    WHEN excluded.window_end > frequency_buckets.window_end
                    THEN excluded.window_end
                    ELSE frequency_buckets.window_end
                END,
                updated_at = excluded.updated_at
            """,
            (bucket_id, normalized, stamp, stamp, stamp),
        )
        con.execute(
            """
            INSERT INTO audit_events (
                event_type, entity_type, entity_id, detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "frequency_question",
                "frequency_bucket",
                bucket_id,
                json.dumps({"at": stamp, "normalized_text": normalized}),
                stamp,
            ),
        )
        con.commit()
        row = con.execute(
            "SELECT * FROM frequency_buckets WHERE normalized_text = ?",
            (normalized,),
        ).fetchone()
    finally:
        con.close()
    return _row_to_bucket(row)


def signals_for_pulse(
    window_days: int = 7,
    threshold: int = 5,
    *,
    db_path: str | Path | None = None,
    as_of: datetime | None = None,
) -> list[FrequencySignal]:
    """Questions seen at least `threshold` times in the rolling window."""
    path = _db_path(db_path)
    init_db(path)
    as_of_dt = _naive_utc(as_of or datetime.now(timezone.utc))
    cutoff = as_of_dt - timedelta(days=window_days)

    con = connect(path)
    try:
        rows = con.execute(
            """
            SELECT detail_json FROM audit_events
            WHERE event_type = 'frequency_question'
            """
        ).fetchall()
    finally:
        con.close()

    grouped: dict[str, list[datetime]] = {}
    for row in rows:
        detail = json.loads(row["detail_json"] or "{}")
        normalized = str(detail.get("normalized_text") or "")
        raw_at = detail.get("at")
        if not normalized or not raw_at:
            continue
        seen = datetime.fromisoformat(str(raw_at))
        if cutoff <= seen <= as_of_dt:
            grouped.setdefault(normalized, []).append(seen)

    signals: list[FrequencySignal] = []
    for normalized, times in grouped.items():
        if len(times) < threshold:
            continue
        signals.append(
            FrequencySignal(
                normalized_text=normalized,
                count=len(times),
                window_days=window_days,
                threshold=threshold,
                first_seen=min(times),
                last_seen=max(times),
            )
        )
    signals.sort(key=lambda s: (-s.count, s.normalized_text))
    return signals


def render_pulse_appendix(signals: list[FrequencySignal]) -> str:
    """Callout for the pulse artifact. Queue counts only — no Play review ids."""
    if not signals:
        return ""
    window_days = signals[0].window_days
    lines = [
        "## Support queue frequency",
        (
            f"Window: rolling {window_days} days. "
            "Counts are support-queue questions, not Play review ids."
        ),
        "",
    ]
    for signal in signals:
        lines.append(
            f"- {signal.normalized_text} — count {signal.count} "
            f"(window {signal.window_days} days)"
        )
    return "\n".join(lines) + "\n"
