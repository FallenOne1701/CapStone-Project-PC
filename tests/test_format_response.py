from src.rag.format_response import format_factual_answer, truncate_to_three_sentences


def test_truncate_to_three_sentences():
    body = "One. Two. Three. Four."
    assert truncate_to_three_sentences(body) == "One. Two. Three."


def test_format_includes_single_link_and_footer():
    out = format_factual_answer(
        "The expense ratio is 0.80%.",
        "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "2025-11-17",
    )
    assert out.count("https://") == 1
    assert "groww.in" in out
    assert "Last updated from sources: 2025-11-17" in out
