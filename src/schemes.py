from __future__ import annotations

from typing import Optional

SCHEMES: dict[str, dict] = {
    "hdfc-mid-cap-fund-direct-growth": {
        "name": "HDFC Mid Cap Fund - Direct Growth",
        "aliases": ["mid cap", "midcap", "hdfc mid cap"],
        "category": "mid-cap",
        "groww_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
    },
    "hdfc-small-cap-fund-direct-growth": {
        "name": "HDFC Small Cap Fund - Direct Growth",
        "aliases": ["small cap", "smallcap", "hdfc small cap"],
        "category": "small-cap",
        "groww_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    "hdfc-gold-etf-fund-of-fund-direct-plan-growth": {
        "name": "HDFC Gold ETF Fund of Fund - Direct Plan Growth",
        "aliases": ["gold", "gold etf", "gold fof"],
        "category": "gold-fof",
        "groww_url": (
            "https://groww.in/mutual-funds/"
            "hdfc-gold-etf-fund-of-fund-direct-plan-growth"
        ),
    },
    "hdfc-large-cap-fund-direct-growth": {
        "name": "HDFC Large Cap Fund - Direct Growth",
        "aliases": ["large cap", "largecap", "hdfc large cap"],
        "category": "large-cap",
        "groww_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    "hdfc-elss-tax-saver-fund-direct-plan-growth": {
        "name": "HDFC ELSS Tax Saver Fund - Direct Plan Growth",
        "aliases": ["elss", "tax saver", "hdfc elss"],
        "category": "elss",
        "groww_url": (
            "https://groww.in/mutual-funds/"
            "hdfc-elss-tax-saver-fund-direct-plan-growth"
        ),
    },
}


def detect_scheme_id(query: str) -> Optional[str]:
    q = query.lower()
    for scheme_id, meta in SCHEMES.items():
        if meta["name"].lower() in q:
            return scheme_id
        for alias in meta["aliases"]:
            if alias in q:
                return scheme_id
    return None
