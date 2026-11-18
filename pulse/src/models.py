from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Review(BaseModel):
    review_id: str
    store: Literal["play"] = "play"
    app_id: str = "com.nextbillion.groww"
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    text: str
    created_at: date
    lang: str | None = None
    theme_id: str | None = None

    @field_validator("text")
    @classmethod
    def non_empty_text(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("review text must be non-empty")
        return v


class Theme(BaseModel):
    theme_id: str
    label: str
    review_ids: list[str] = Field(default_factory=list)
    count: int = 0


class ThemeResult(BaseModel):
    themes: list[Theme] = Field(max_length=5)
    top_theme_ids: list[str] = Field(max_length=3)


class PulseDoc(BaseModel):
    title: str
    window_start: date
    window_end: date
    review_count: int
    themes: list[str]  # top 3 labels
    quotes: list[str]  # exactly 3
    actions: list[str]  # exactly 3
    body_markdown: str
    created_at: datetime
