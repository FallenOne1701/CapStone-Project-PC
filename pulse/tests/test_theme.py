from src.models import Theme, ThemeResult
from src.theme import enforce_theme_cap, rank_top_themes


def test_enforce_theme_cap_keeps_five():
    themes = [
        Theme(theme_id=f"t{i}", label=f"L{i}", review_ids=[str(i)], count=i)
        for i in range(1, 8)
    ]
    capped = enforce_theme_cap(themes, max_themes=5)
    assert len(capped) == 5
    assert capped[0].count >= capped[-1].count


def test_rank_top_themes():
    result = ThemeResult(
        themes=[
            Theme(theme_id="a", label="KYC", review_ids=["1", "2"], count=2),
            Theme(theme_id="b", label="Pay", review_ids=["3"], count=1),
            Theme(theme_id="c", label="Crash", review_ids=["4", "5", "6"], count=3),
        ],
        top_theme_ids=[],
    )
    ranked = rank_top_themes(result, n=3)
    assert ranked.top_theme_ids[0] == "c"
    assert len(ranked.top_theme_ids) == 3
