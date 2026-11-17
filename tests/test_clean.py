from src.ingest.clean import normalize_text, extract_text
from pathlib import Path


def test_normalize_collapses_whitespace_and_keeps_ratios():
    raw = "Expense Ratio:\n\n  0.75%   \nExit Load:\t1%"
    out = normalize_text(raw)
    # Plan normalize collapses spaces/tabs but preserves newlines (needed for section headers).
    assert "Expense Ratio:" in out
    assert "0.75%" in out
    assert "Exit Load: 1%" in out
    assert "\t" not in out
    assert "  " not in out.replace("\n", "")


def test_extract_text_from_html_strips_scripts(tmp_path: Path):
    html = tmp_path / "sample.html"
    html.write_text(
        "<html><head><script>evil()</script><style>.x{}</style></head>"
        "<body><nav>Skip</nav><p>Expense Ratio: 0.75%</p></body></html>",
        encoding="utf-8",
    )
    out = extract_text(html)
    assert "evil" not in out
    assert "Expense Ratio: 0.75%" in out
