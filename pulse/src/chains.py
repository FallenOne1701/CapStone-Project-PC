from __future__ import annotations

from typing import TypeVar

from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel

from src.config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


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


def structured_invoke(
    llm: ChatGroq,
    prompt_chain: Runnable,
    schema: type[T],
    inputs: dict,
) -> T:
    """Prefer Groq JSON schema (strict-capable); fall back to tools then JSON object mode."""
    errors: list[Exception] = []
    for kwargs in (
        {"method": "json_schema"},
        {},
        {"method": "json_mode"},
    ):
        try:
            return (
                prompt_chain | llm.with_structured_output(schema, **kwargs)
            ).invoke(inputs)
        except Exception as e:  # noqa: BLE001 — try next structured-output method
            errors.append(e)
    raise errors[-1]
