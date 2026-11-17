from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.rag.retrieve import detect_section, retrieve


def test_detect_section_expense_and_lockin():
    assert detect_section("What is the expense ratio?") == "expense ratio"
    assert detect_section("ELSS lock-in period") == "lock-in"
    assert detect_section("minimum SIP HDFC Small Cap") == "minimum sip"


def test_detect_section_prefers_specific_needles():
    assert detect_section("What is the investment objective?") == "investment objective"
    assert detect_section("lump sum amount") == "minimum lumpsum"
    assert detect_section("riskometer level") == "riskometer"
    assert detect_section("unknown topic") is None


def test_retrieve_builds_scheme_and_section_where(monkeypatch):
    settings = MagicMock()
    settings.embed_model = "fake-model"
    settings.chroma_path = Path("corpus_index")
    settings.similarity_threshold = 0.55
    settings.top_k = 3

    fake_model = MagicMock()
    fake_model.encode.return_value = [[0.1, 0.2, 0.3]]

    collection = MagicMock()
    collection.query.return_value = {
        "documents": [
            ["HDFC Large Cap Fund - Direct Growth. Expense ratio\nExpense ratio is 0.80%."]
        ],
        "metadatas": [
            [
                {
                    "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                    "as_of_date": "2025-11-17",
                    "scheme_id": "hdfc-large-cap-fund-direct-growth",
                    "section": "expense ratio",
                }
            ]
        ],
        "distances": [[0.1]],
    }

    client = MagicMock()
    client.get_collection.return_value = collection

    monkeypatch.setattr(
        "src.rag.retrieve.SentenceTransformer",
        lambda *_a, **_k: fake_model,
    )
    monkeypatch.setattr(
        "src.rag.retrieve.chromadb.PersistentClient",
        lambda **_k: client,
    )

    chunks = retrieve(
        "What is the expense ratio of HDFC Large Cap Fund?",
        settings,
        scheme_id="hdfc-large-cap-fund-direct-growth",
    )

    assert len(chunks) == 1
    assert chunks[0].section == "expense ratio"
    assert chunks[0].scheme_id == "hdfc-large-cap-fund-direct-growth"
    assert chunks[0].score == pytest.approx(0.9)
    kwargs = collection.query.call_args.kwargs
    assert kwargs["where"] == {
        "$and": [
            {"scheme_id": "hdfc-large-cap-fund-direct-growth"},
            {"section": "expense ratio"},
        ]
    }
    assert kwargs["n_results"] == 2


def test_retrieve_retries_scheme_only_when_section_filter_empty(monkeypatch):
    settings = MagicMock()
    settings.embed_model = "fake-model"
    settings.chroma_path = Path("corpus_index")
    settings.similarity_threshold = 0.55
    settings.top_k = 3

    fake_model = MagicMock()
    fake_model.encode.return_value = [[0.1, 0.2, 0.3]]

    collection = MagicMock()
    collection.query.side_effect = [
        {"documents": [[]], "metadatas": [[]], "distances": [[]]},
        {
            "documents": [["HDFC Large Cap. Expense ratio is 0.80%."]],
            "metadatas": [
                [
                    {
                        "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                        "as_of_date": "2025-11-17",
                        "scheme_id": "hdfc-large-cap-fund-direct-growth",
                        "section": "expense ratio",
                    }
                ]
            ],
            "distances": [[0.2]],
        },
    ]

    client = MagicMock()
    client.get_collection.return_value = collection
    monkeypatch.setattr(
        "src.rag.retrieve.SentenceTransformer",
        lambda *_a, **_k: fake_model,
    )
    monkeypatch.setattr(
        "src.rag.retrieve.chromadb.PersistentClient",
        lambda **_k: client,
    )

    chunks = retrieve(
        "What is the expense ratio of HDFC Large Cap Fund?",
        settings,
        scheme_id="hdfc-large-cap-fund-direct-growth",
    )
    assert len(chunks) == 1
    assert collection.query.call_count == 2
    second_where = collection.query.call_args_list[1].kwargs["where"]
    assert second_where == {"scheme_id": "hdfc-large-cap-fund-direct-growth"}


@pytest.mark.skipif(
    not Path("corpus_index").exists(), reason="needs built Chroma index"
)
def test_retrieve_large_cap_expense_ratio(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-for-settings")
    from src.config import get_settings

    # Prefer Task 7 threshold guidance for live smoke.
    monkeypatch.setenv("SIMILARITY_THRESHOLD", "0.55")
    chunks = retrieve(
        "What is the expense ratio of HDFC Large Cap Fund?",
        get_settings(),
        scheme_id="hdfc-large-cap-fund-direct-growth",
    )
    assert chunks
    assert chunks[0].section == "expense ratio"
    assert chunks[0].scheme_id == "hdfc-large-cap-fund-direct-growth"
    assert chunks[0].source_url.startswith("https://groww.in/")
    assert chunks[0].score >= 0.55
