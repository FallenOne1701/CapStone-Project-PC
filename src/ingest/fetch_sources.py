from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from src.config import ROOT
from src.ingest.clean import extract_text

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
ALLOWED_HOST = "groww.in"


def _assert_groww_url(url: str) -> None:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host != ALLOWED_HOST:
        raise ValueError(f"Refusing non-Groww URL: {url}")


def fetch_all(
    manifest_path: Path,
    raw_dir: Path,
    processed_dir: Path,
    force: bool = False,
) -> list[Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    processed_paths: list[Path] = []
    for doc in manifest["documents"]:
        source_url = doc["source_url"]
        _assert_groww_url(source_url)
        local_name = doc["local_name"]
        raw_path = raw_dir / local_name
        stem = Path(local_name).stem
        processed_path = processed_dir / f"{stem}.txt"

        if force or not raw_path.exists():
            resp = session.get(source_url, timeout=60)
            resp.raise_for_status()
            raw_path.write_bytes(resp.content)

        text = extract_text(raw_path)
        processed_path.write_text(text, encoding="utf-8")
        processed_paths.append(processed_path)

    return processed_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and clean Groww scheme pages")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "manifest.json",
    )
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument(
        "--processed-dir", type=Path, default=ROOT / "data" / "processed"
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    paths = fetch_all(args.manifest, args.raw_dir, args.processed_dir, force=args.force)
    print(f"Processed {len(paths)} documents")
    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
