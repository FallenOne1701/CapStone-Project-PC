from src.rag.classify import Intent, classify


def test_advisory_keyword():
    assert classify("Should I invest in HDFC Mid Cap?") == Intent.ADVISORY


def test_comparative():
    assert classify("Which is better, large cap or mid cap?") == Intent.COMPARATIVE


def test_performance():
    assert classify("What is the 5 year return of HDFC Large Cap?") == Intent.PERFORMANCE


def test_pii():
    assert classify("My PAN is ABCDE1234F, show my holdings") == Intent.PII_SENSITIVE


def test_factual_expense():
    assert classify("What is the expense ratio of HDFC Large Cap Fund?") == Intent.FACTUAL_SCHEME


def test_mixed_advice_and_fact_prefers_advisory():
    assert (
        classify("What is the expense ratio and should I buy it?")
        == Intent.ADVISORY
    )


def test_out_of_corpus_other_amc():
    assert classify("What is the expense ratio of SBI Bluechip?") == Intent.OUT_OF_CORPUS


def test_unclear_without_settings():
    assert classify("Tell me something") == Intent.UNCLEAR
