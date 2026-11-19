from src.pii import contains_pii, redact_pii

PAN = "ABCDE1234F"
PHONE = "9876543210"
EMAIL = "user@example.com"
ACCOUNT = "123456789012"


def test_contains_pii_detects_pan():
    assert contains_pii(f"my pan is {PAN}") is True


def test_contains_pii_detects_phone():
    assert contains_pii(f"call me at {PHONE}") is True


def test_contains_pii_detects_email():
    assert contains_pii(f"email {EMAIL} please") is True


def test_contains_pii_detects_account_like():
    assert contains_pii(f"account {ACCOUNT}") is True


def test_contains_pii_clean_text_is_false():
    assert contains_pii("What is the exit load on Groww funds?") is False


def test_redact_pii_removes_pan():
    out = redact_pii(f"my pan is {PAN}")
    assert PAN not in out
    assert contains_pii(out) is False


def test_redact_pii_removes_phone():
    out = redact_pii(f"call me at {PHONE}")
    assert PHONE not in out
    assert contains_pii(out) is False


def test_redact_pii_removes_email():
    out = redact_pii(f"email {EMAIL} please")
    assert EMAIL not in out
    assert contains_pii(out) is False


def test_redact_pii_removes_account_like():
    out = redact_pii(f"account {ACCOUNT}")
    assert ACCOUNT not in out
    assert contains_pii(out) is False
