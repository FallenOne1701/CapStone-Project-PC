from __future__ import annotations

from pydantic import BaseModel, Field

_FEE_CUES = (
    "fee",
    "fees",
    "charge",
    "charges",
    "brokerage",
    "expense ratio",
    "exit load",
    "stamp duty",
    "dp charge",
    "account maintenance",
    "amc",
)


class Theme(BaseModel):
    theme_id: str
    label: str
    review_ids: list[str] = Field(default_factory=list)
    count: int = 0


class ThemeResult(BaseModel):
    themes: list[Theme] = Field(default_factory=list, max_length=5)
    top_theme_ids: list[str] = Field(default_factory=list, max_length=3)


def detect_fee_confusion(themes: ThemeResult) -> bool:
    """Return True when weekly themes indicate fee/charge confusion."""
    for theme in themes.themes:
        label = (theme.label or "").lower()
        if any(cue in label for cue in _FEE_CUES):
            return True
    return False
