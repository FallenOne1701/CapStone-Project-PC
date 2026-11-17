import json
from pathlib import Path
from urllib.parse import urlparse

from src.schemes import SCHEMES

ALLOWED_HOST = "groww.in"
DISALLOWED = (
    "hdfcfund.com",
    "amfiindia.com",
    "sebi.gov.in",
    "moneycontrol.com",
    "valueresearchonline.com",
)
REQUIRED_PATHS = {
    "/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    "/mutual-funds/hdfc-small-cap-fund-direct-growth",
    "/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
    "/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
}


def test_manifest_is_groww_scheme_pages_only():
    manifest = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["documents"]) == 5
    paths = set()
    for doc in manifest["documents"]:
        parsed = urlparse(doc["source_url"])
        host = parsed.netloc.lower().removeprefix("www.")
        assert host == ALLOWED_HOST
        assert not any(bad in host for bad in DISALLOWED)
        assert doc["doc_type"] == "groww_scheme_page"
        assert doc["scheme_id"]
        paths.add(parsed.path.rstrip("/"))
    assert paths == REQUIRED_PATHS


def test_schemes_groww_url_matches_manifest():
    manifest = json.loads(Path("data/manifest.json").read_text(encoding="utf-8"))
    by_id = {doc["scheme_id"]: doc["source_url"] for doc in manifest["documents"]}
    assert set(by_id) == set(SCHEMES)
    for scheme_id, meta in SCHEMES.items():
        assert meta["groww_url"] == by_id[scheme_id]
