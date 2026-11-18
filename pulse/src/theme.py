from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.chains import build_chat_model, load_prompt, structured_invoke
from src.config import Settings, get_settings
from src.models import Review, Theme, ThemeResult


class LLMTheme(BaseModel):
    theme_id: str
    label: str
    review_ids: list[str] = Field(default_factory=list)


class LLMThemePayload(BaseModel):
    themes: list[LLMTheme] = Field(default_factory=list, max_length=5)


def enforce_theme_cap(themes: list[Theme], max_themes: int = 5) -> list[Theme]:
    ordered = sorted(themes, key=lambda t: t.count, reverse=True)
    return ordered[:max_themes]


def rank_top_themes(result: ThemeResult, n: int = 3) -> ThemeResult:
    ordered = sorted(result.themes, key=lambda t: t.count, reverse=True)
    top = [t.theme_id for t in ordered[:n]]
    return ThemeResult(themes=enforce_theme_cap(result.themes), top_theme_ids=top)


def _reviews_for_prompt(reviews: list[Review], limit: int = 40) -> str:
    # Keep the prompt small — large batches make Groq json_schema fail empty.
    lines = []
    for r in reviews[:limit]:
        lines.append(f"- id={r.review_id} rating={r.rating}: {r.text[:160]}")
    return "\n".join(lines)


def cluster_themes(
    reviews: list[Review], settings: Settings | None = None
) -> ThemeResult:
    if not reviews:
        raise ValueError("cannot cluster themes: no reviews in window")
    settings = settings or get_settings()
    llm = build_chat_model(settings)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("theme_system.txt", settings)),
            (
                "human",
                "Return ONE object: {{\"themes\":[{{\"theme_id\",\"label\",\"review_ids\"}}…]}} "
                "with at most 5 themes. Each theme lists review_ids that belong to it. "
                "Do NOT return a per-review list.\nReviews:\n{reviews}",
            ),
        ]
    )
    payload: LLMThemePayload = structured_invoke(
        llm, prompt, LLMThemePayload, {"reviews": _reviews_for_prompt(reviews)}
    )
    themes: list[Theme] = []
    for t in payload.themes:
        ids = [i for i in t.review_ids if i]
        themes.append(
            Theme(
                theme_id=t.theme_id,
                label=t.label.strip(),
                review_ids=ids,
                count=len(ids),
            )
        )
    themes = enforce_theme_cap(themes, 5)
    if not themes:
        raise ValueError("theme model returned no themes")
    return rank_top_themes(ThemeResult(themes=themes, top_theme_ids=[]), n=3)


def save_themes(result: ThemeResult, path) -> None:
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
