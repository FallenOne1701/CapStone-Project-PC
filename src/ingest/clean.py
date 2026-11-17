from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        parts = [page.extract_text() or "" for page in reader.pages]
        return normalize_text("\n".join(parts))
    if path.suffix.lower() in {".html", ".htm"}:
        soup = BeautifulSoup(
            path.read_text(encoding="utf-8", errors="ignore"), "html.parser"
        )
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return normalize_text(soup.get_text("\n"))
    return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))
