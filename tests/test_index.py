from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.ingest.index import build_index


class _FakeEmbedding:
    def __init__(self, dim: int = 8):
        self.dim = dim

    def encode(self, texts, show_progress_bar=False):
        return [[float(len(t) % 7)] * self.dim for t in texts]


def test_build_index_upserts_chunks_with_groww_metadata(tmp_path: Path, monkeypatch):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "hdfc-large-cap-fund-direct-growth.txt").write_text(
        "Expense Ratio\nDirect plan expense ratio is 0.80%.\n",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "amc": "HDFC",
                "documents": [
                    {
                        "scheme_id": "hdfc-large-cap-fund-direct-growth",
                        "scheme_name": "HDFC Large Cap Fund - Direct Growth",
                        "doc_type": "groww_scheme_page",
                        "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                        "as_of_date": "2025-11-17",
                        "local_name": "hdfc-large-cap-fund-direct-growth.html",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    chroma_path = tmp_path / "chroma"
    settings = MagicMock()
    settings.embed_model = "fake-model"
    settings.chroma_path = chroma_path

    monkeypatch.setattr(
        "src.ingest.index.SentenceTransformer",
        lambda *_a, **_k: _FakeEmbedding(),
    )

    count = build_index(processed, manifest_path, settings)
    assert count >= 1

    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_path))
    coll = client.get_collection("mf_faq")
    assert coll.count() == count
    got = coll.get(include=["metadatas", "documents"])
    meta = got["metadatas"][0]
    assert meta["scheme_id"] == "hdfc-large-cap-fund-direct-growth"
    assert "groww.in" in meta["source_url"]
    assert meta["as_of_date"] == "2025-11-17"
    assert got["documents"][0].strip()
