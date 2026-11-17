from __future__ import annotations

import argparse
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import ROOT, Settings, get_settings
from src.ingest.chunk import chunk_document

COLLECTION_NAME = "mf_faq"
BATCH_SIZE = 32


def _meta_as_strings(chunk) -> dict[str, str]:
    return {
        "chunk_id": str(chunk.chunk_id),
        "scheme_id": str(chunk.scheme_id),
        "scheme_name": str(chunk.scheme_name),
        "amc": str(chunk.amc),
        "doc_type": str(chunk.doc_type),
        "source_url": str(chunk.source_url),
        "as_of_date": str(chunk.as_of_date),
        "section": str(chunk.section),
    }


def build_index(
    processed_dir: Path, manifest_path: Path, settings: Settings
) -> int:
    """Chunk all processed docs from manifest and upsert into Chroma. Returns chunk count."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    amc = manifest.get("amc", "HDFC")

    all_chunks = []
    for doc in manifest["documents"]:
        stem = Path(doc["local_name"]).stem
        text_path = processed_dir / f"{stem}.txt"
        if not text_path.exists():
            raise FileNotFoundError(f"Missing processed text: {text_path}")
        text = text_path.read_text(encoding="utf-8")
        meta = {
            "scheme_id": doc["scheme_id"],
            "scheme_name": doc["scheme_name"],
            "amc": amc,
            "doc_type": doc["doc_type"],
            "source_url": doc["source_url"],
            "as_of_date": doc["as_of_date"],
        }
        all_chunks.extend(chunk_document(text, meta))

    if not all_chunks:
        return 0

    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_path))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    model = SentenceTransformer(settings.embed_model)

    for start in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[start : start + BATCH_SIZE]
        texts = [c.text for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False)
        # sentence-transformers may return numpy array
        vectors = [list(map(float, row)) for row in embeddings]
        collection.upsert(
            ids=[c.chunk_id for c in batch],
            documents=texts,
            embeddings=vectors,
            metadatas=[_meta_as_strings(c) for c in batch],
        )

    return len(all_chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma index from processed docs")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "manifest.json",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=ROOT / "data" / "processed",
    )
    args = parser.parse_args()

    settings = get_settings()
    n = build_index(args.processed_dir, args.manifest, settings)
    print(f"Indexed {n} chunks")


if __name__ == "__main__":
    main()
