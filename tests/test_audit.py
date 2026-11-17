from src.rag.audit import audit_response

GOOD = (
    "The expense ratio for the Direct plan is 0.80%. Exit load may apply as per the scheme page.\n"
    "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
    "Last updated from sources: 2025-11-17"
)


def test_good_response_passes():
    assert audit_response(GOOD).ok


def test_advice_phrase_fails():
    bad = GOOD.replace("0.80%", "0.80%. I recommend buying this fund")
    result = audit_response(bad)
    assert not result.ok
    assert result.reasons


def test_missing_footer_fails():
    bad = (
        "The expense ratio is 0.80%.\n"
        "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    )
    assert not audit_response(bad).ok


def test_too_many_sentences_fails():
    bad = (
        "One. Two. Three. Four.\n"
        "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth\n"
        "Last updated from sources: 2025-11-17"
    )
    assert not audit_response(bad).ok


def test_multiple_urls_fails():
    bad = (
        "The expense ratio is 0.80%.\n"
        "Source: https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth "
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n"
        "Last updated from sources: 2025-11-17"
    )
    assert not audit_response(bad).ok


def test_pan_like_pattern_fails():
    bad = GOOD.replace("0.80%", "0.80% for ABCDE1234F")
    assert not audit_response(bad).ok
