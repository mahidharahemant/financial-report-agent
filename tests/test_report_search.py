from src.report_search import extract_sections


def test_extract_sections_finds_common_items():
    text = (
        "Item 1. Business The company sells software and services. "
        "Item 1A. Risk Factors Cybersecurity and regulatory risks matter. "
        "Item 7. Management's Discussion and Analysis Revenue increased."
    )
    sections = extract_sections(text)
    assert "Business" in sections
    assert "Risk Factors" in sections
    assert "Management Discussion and Analysis" in sections


def test_extract_sections_empty_text():
    assert extract_sections("") == {}
