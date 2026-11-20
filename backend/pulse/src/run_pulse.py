from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from src.audit import audit_pulse
from src.clean import clean_reviews
from src.config import get_settings
from src.fetch_play import (
    fetch_play_reviews,
    filter_by_window,
    load_reviews_jsonl,
    save_raw_jsonl,
    window_bounds,
)
from src.theme import cluster_themes, save_themes
from src.write_pulse import write_pulse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Groww weekly review pulse")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use data/samples/reviews_sample.jsonl instead of live Play fetch",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch public Play reviews (default if --sample not set)",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    settings.out_dir.mkdir(parents=True, exist_ok=True)
    settings.data_clean.mkdir(parents=True, exist_ok=True)
    settings.data_raw.mkdir(parents=True, exist_ok=True)

    # Default = sample (safe). --live fetches public Play reviews.
    if args.live:
        reviews = fetch_play_reviews(settings)
        save_raw_jsonl(
            reviews, settings.data_raw / f"play-{date.today().isoformat()}.jsonl"
        )
    else:
        sample = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "samples"
            / "reviews_sample.jsonl"
        )
        reviews = load_reviews_jsonl(sample)

    start, end = window_bounds(settings.pulse_lookback_weeks)
    reviews = filter_by_window(reviews, start, end)
    reviews = clean_reviews(reviews)
    if not reviews:
        print("ERROR: no reviews in lookback window after clean", file=sys.stderr)
        return 1

    save_raw_jsonl(reviews, settings.data_clean / "reviews.jsonl")
    themes = cluster_themes(reviews, settings)
    save_themes(themes, settings.out_dir / "themes.json")
    doc = write_pulse(reviews, themes, settings)
    audit = audit_pulse(doc, reviews)
    if not audit.ok:
        print("AUDIT FAILED:", *audit.errors, sep="\n - ", file=sys.stderr)
        return 2

    out_path = settings.out_dir / f"pulse-{end.isoformat()}.md"
    out_path.write_text(doc.body_markdown, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Themes: {settings.out_dir / 'themes.json'}")
    print("Next: follow Docs-MCP-&-RAG/mcp-runbook.md to publish Doc + Gmail draft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
