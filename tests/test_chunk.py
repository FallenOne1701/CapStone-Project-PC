from src.ingest.chunk import chunk_document

META = {
    "scheme_id": "hdfc-large-cap-fund-direct-growth",
    "scheme_name": "HDFC Large Cap Fund - Direct Growth",
    "amc": "HDFC",
    "doc_type": "groww_scheme_page",
    "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    "as_of_date": "2025-11-17",
}


def test_chunks_carry_required_metadata_and_stay_single_scheme():
    text = (
        "Expense Ratio\n"
        + ("Direct plan expense ratio is 0.80%. " * 40)
        + "\nExit Load\n"
        + ("Exit load is 1% if redeemed within 1 year. " * 40)
    )
    chunks = chunk_document(text, META)
    assert len(chunks) >= 1
    for c in chunks:
        assert c.scheme_id == META["scheme_id"]
        assert c.source_url.startswith("https://")
        assert c.as_of_date == "2025-11-17"
        assert "groww.in" in c.source_url
        assert c.text.strip()


def test_chunk_ids_are_stable_and_section_set():
    text = "Expense Ratio\nDirect plan expense ratio is 0.80%.\n\nExit Load\nExit load is 1%."
    chunks = chunk_document(text, META)
    assert chunks[0].chunk_id == f"{META['scheme_id']}-{META['doc_type']}-0"
    assert any(c.section.lower().startswith("expense") or c.section == "expense ratio" for c in chunks)


def test_historic_exit_load_row_is_not_a_section_header():
    text = (
        "Exit Load\nExit load of 1% if redeemed within 1 year.\n"
        "Exit load of 1% if redeemed within 18 months\n"
        "Minimum SIP\nMinimum SIP amount is Rs 100."
    )
    chunks = chunk_document(text, META)
    sections = {c.section for c in chunks}
    assert "exit load" in sections
    assert "minimum sip" in sections
    assert not any("18 months" in s for s in sections)
