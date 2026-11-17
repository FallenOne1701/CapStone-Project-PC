import json
from pathlib import Path

from src.ingest.clean import extract_as_of_date, extract_text, normalize_text


def test_normalize_collapses_whitespace_and_keeps_ratios():
    raw = "Expense Ratio:\n\n  0.75%   \nExit Load:\t1%"
    out = normalize_text(raw)
    # Plan normalize collapses spaces/tabs but preserves newlines (needed for section headers).
    assert "Expense Ratio:" in out
    assert "0.75%" in out
    assert "Exit Load: 1%" in out
    assert "\t" not in out
    assert "  " not in out.replace("\n", "")


def test_extract_text_from_html_strips_nav_and_scripts(tmp_path: Path):
    html = tmp_path / "sample.html"
    html.write_text(
        "<html><head><script>evil()</script><style>.x{}</style></head>"
        "<body><nav>Skip me menu</nav><p>Expense Ratio: 0.75%</p></body></html>",
        encoding="utf-8",
    )
    out = extract_text(html)
    assert "evil" not in out
    assert "Skip me menu" not in out
    assert "Expense Ratio: 0.75%" in out


def _groww_next_data_html() -> str:
    payload = {
        "props": {
            "pageProps": {
                "mfServerSideData": {
                    "scheme_name": "HDFC Large Cap Fund Direct Growth",
                    "fund_house": "HDFC Mutual Fund",
                    "category": "Equity",
                    "sub_category": "Large Cap",
                    "plan_type": "Direct",
                    "description": "Invests predominantly in Large-Cap companies.",
                    "expense_ratio": "0.80",
                    "base_expense_ratio": "0.70",
                    "exit_load": "Exit load of 1% if redeemed within 1 year",
                    "min_sip_investment": 100,
                    "min_investment_amount": 100,
                    "benchmark": "NIFTY 100 TRI",
                    "nfo_risk": "Very High Riskometer",
                    "lock_in": {"years": None, "months": None, "days": None},
                    "nav": 100.0,
                    "nav_date": "16-Nov-2026",
                    "stamp_duty": "0.005%",
                    "peerComparison": [
                        {
                            "scheme_name": "Invesco India Largecap Fund",
                            "return1y": 12.5,
                        }
                    ],
                    "return_stats": [{"return1y": 0.31, "return3y": 10.29}],
                    "simple_return": {"return1y": 0.31},
                    "sip_return": {"return1y": 10.19},
                    "historic_exit_loads": [
                        {
                            "note": "Exit load of 1% if redeemed within 18 months",
                            "as_on_date": "2015-02-16T00:00:00",
                        }
                    ],
                    "stats": [{"type": "FUND_RETURN", "stat_1y": 0.31}],
                }
            }
        }
    }
    return (
        "<html><head><title>x</title>"
        f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
        "</head><body><nav>Stocks Invest in Stocks SIP calculator Compare Funds</nav>"
        "<h1>HDFC Large Cap Fund Direct Growth</h1></body></html>"
    )


def test_extract_next_data_keeps_facts_drops_chrome_peers_returns_history(tmp_path: Path):
    html = tmp_path / "scheme.html"
    html.write_text(_groww_next_data_html(), encoding="utf-8")
    out = extract_text(html)
    assert "Expense Ratio" in out
    assert "0.80" in out
    assert "Exit Load" in out
    assert "Minimum SIP" in out
    assert "Investment Objective" in out
    assert "Invesco" not in out
    assert "return1y" not in out
    assert "18 months" not in out
    assert "SIP calculator" not in out
    assert "Compare Funds" not in out
    assert extract_as_of_date(html) == "2026-11-16"
