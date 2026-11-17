from __future__ import annotations

import re
from dataclasses import dataclass


# Canonical section headers only (line must be exactly the header, case-insensitive).
SECTION_HEADERS = re.compile(
    r"(?im)^(expense ratio|exit load|minimum sip|minimum lumpsum|riskometer|"
    r"benchmark|lock-in|investment objective|scheme|fund house|category|"
    r"stamp duty|nav)$"
)


@dataclass
class Chunk:
    chunk_id: str
    scheme_id: str
    scheme_name: str
    amc: str
    doc_type: str
    source_url: str
    as_of_date: str
    section: str
    text: str


def _split_fixed(text: str, max_chars: int, overlap: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if overlap >= max_chars:
        overlap = max(0, max_chars // 8)
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end].strip())
        if end >= len(text):
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start
    return [p for p in parts if p]


def _sections(text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_HEADERS.finditer(text))
    if not matches:
        return [("general", text)]

    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("general", preamble))

    for i, match in enumerate(matches):
        section_name = match.group(0).strip().lower()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        content = f"{match.group(0).strip()}\n{body}".strip() if body else match.group(0).strip()
        sections.append((section_name, content))
    return sections


def chunk_document(
    text: str, meta: dict, max_chars: int = 600, overlap: int = 80
) -> list[Chunk]:
    chunks: list[Chunk] = []
    index = 0
    scheme_prefix = f"{meta['scheme_name']}. "
    for section_name, section_text in _sections(text):
        for piece in _split_fixed(section_text, max_chars, overlap):
            # Prefix scheme name in embedded text to reduce cross-scheme collisions.
            embedded = piece if piece.lower().startswith(meta["scheme_name"].lower()) else (
                scheme_prefix + piece
            )
            chunks.append(
                Chunk(
                    chunk_id=f"{meta['scheme_id']}-{meta['doc_type']}-{index}",
                    scheme_id=meta["scheme_id"],
                    scheme_name=meta["scheme_name"],
                    amc=meta["amc"],
                    doc_type=meta["doc_type"],
                    source_url=meta["source_url"],
                    as_of_date=meta["as_of_date"],
                    section=section_name,
                    text=embedded,
                )
            )
            index += 1
    return chunks
