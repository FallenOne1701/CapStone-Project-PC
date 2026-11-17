from __future__ import annotations

import re


def truncate_to_three_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p for p in parts if p]
    return " ".join(parts[:3]).strip()


def format_factual_answer(body: str, source_url: str, as_of_date: str) -> str:
    body = truncate_to_three_sentences(body)
    return f"{body}\nSource: {source_url}\nLast updated from sources: {as_of_date}"
