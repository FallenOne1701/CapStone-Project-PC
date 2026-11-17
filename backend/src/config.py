from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    chat_model: str
    groq_base_url: str
    embed_model: str
    chroma_path: Path
    similarity_threshold: float
    top_k: int
    educational_link: str = (
        "https://www.amfiindia.com/investor-corner/online-centre/onlinecentrelanding"
    )


def get_settings() -> Settings:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY missing. Copy .env.example to .env and set the key."
        )
    return Settings(
        groq_api_key=key,
        chat_model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b"),
        groq_base_url=os.getenv(
            "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
        ),
        embed_model=os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        chroma_path=ROOT / os.getenv("CHROMA_PATH", "corpus_index"),
        similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.35")),
        top_k=int(os.getenv("TOP_K", "4")),
    )


def get_groq_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
