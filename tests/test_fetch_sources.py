import json
from pathlib import Path

from src.ingest.fetch_sources import fetch_all


def test_fetch_all_updates_as_of_date_from_page(tmp_path: Path, monkeypatch):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir()
    html = Path("data/fixtures/sample_groww_next_data.html").read_text(encoding="utf-8")
    local_name = "hdfc-large-cap-fund-direct-growth.html"
    (raw_dir / local_name).write_text(html, encoding="utf-8")

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
                        "local_name": local_name,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def _fail_get(*_a, **_k):
        raise AssertionError("should not download when raw exists")

    monkeypatch.setattr("src.ingest.fetch_sources.requests.Session.get", _fail_get)

    paths = fetch_all(manifest_path, raw_dir, processed_dir, force=False)
    assert len(paths) == 1
    text = paths[0].read_text(encoding="utf-8")
    assert "Expense Ratio" in text
    assert "Invesco" not in text

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated["documents"][0]["as_of_date"] == "2026-11-16"
