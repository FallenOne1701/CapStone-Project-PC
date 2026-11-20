from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PACKAGE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_chat_model: str = Field(
        default="openai/gpt-oss-120b", alias="GROQ_CHAT_MODEL"
    )
    support_deck_db: Path = Field(
        default=PACKAGE_ROOT / "data" / "support_deck.db",
        alias="SUPPORT_DECK_DB",
    )
    pulse_root: Path = Field(default=PACKAGE_ROOT.parent / "pulse", alias="PULSE_ROOT")
    backend_root: Path = Field(
        default=PACKAGE_ROOT.parent / "backend", alias="BACKEND_ROOT"
    )
    pulse_lookback_weeks: int = Field(default=10, alias="PULSE_LOOKBACK_WEEKS")
    pulse_app_id: str = Field(
        default="com.nextbillion.groww", alias="PULSE_APP_ID"
    )
    pulse_doc_id: str = Field(default="", alias="PULSE_DOC_ID")
    pulse_draft_to: str = Field(default="", alias="PULSE_DRAFT_TO")
    support_deck_api_prefix: str = Field(
        default="/api/support-deck", alias="SUPPORT_DECK_API_PREFIX"
    )
    frequency_threshold: int = Field(default=5, alias="FREQUENCY_THRESHOLD")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    db = settings.support_deck_db
    if not db.is_absolute():
        settings.support_deck_db = (PACKAGE_ROOT / db).resolve()
    return settings
