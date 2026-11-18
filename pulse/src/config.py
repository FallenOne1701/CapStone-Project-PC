from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PULSE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PULSE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_chat_model: str = "openai/gpt-oss-120b"
    pulse_lookback_weeks: int = 10
    pulse_app_id: str = "com.nextbillion.groww"
    pulse_lang: str = "en"
    pulse_country: str = "in"
    pulse_draft_to: str = ""
    pulse_max_reviews: int = 500

    @property
    def data_raw(self) -> Path:
        return PULSE_ROOT / "data" / "raw"

    @property
    def data_clean(self) -> Path:
        return PULSE_ROOT / "data" / "clean"

    @property
    def out_dir(self) -> Path:
        return PULSE_ROOT / "out"

    @property
    def prompts_dir(self) -> Path:
        return PULSE_ROOT / "prompts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
