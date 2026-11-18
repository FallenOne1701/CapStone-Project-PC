from __future__ import annotations

from langchain_groq import ChatGroq

from src.config import Settings, get_settings


def load_prompt(name: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    path = settings.prompts_dir / name
    return path.read_text(encoding="utf-8")


def build_chat_model(settings: Settings | None = None) -> ChatGroq:
    settings = settings or get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required for theme/pulse chains")
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_chat_model,
        temperature=0.2,
    )
