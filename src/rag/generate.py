from __future__ import annotations

from src.config import ROOT, Settings, get_groq_client
from src.rag.format_response import format_factual_answer
from src.rag.retrieve import RetrievedChunk

SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system_factual.txt"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _format_context(chunks: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        blocks.append(
            f"[{i}] scheme_id={chunk.scheme_id} section={chunk.section}\n{chunk.text}"
        )
    return "\n\n".join(blocks)


def generate_factual_answer(
    query: str, chunks: list[RetrievedChunk], settings: Settings
) -> str:
    """Return plain model body text only (no citation/footer)."""
    system_prompt = _load_system_prompt()
    user_payload = (
        f"Question:\n{query}\n\n"
        f"Context:\n{_format_context(chunks)}\n\n"
        "Answer using only the context. Do not include a Source URL or footer."
    )
    client = get_groq_client(settings)
    response = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.0,
    )
    content = response.choices[0].message.content
    return (content or "").strip()


def answer_from_chunks(
    query: str, chunks: list[RetrievedChunk], settings: Settings
) -> str:
    body = generate_factual_answer(query, chunks, settings)
    top = chunks[0]
    return format_factual_answer(body, top.source_url, top.as_of_date)
