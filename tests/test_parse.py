from pathlib import Path

from app.parse_xml import parse_law_xml


FIXTURE = Path(__file__).parent / "fixtures" / "burlg_mini.xml"


def test_parse_burlg_paragraph_three():
    chunks = parse_law_xml(FIXTURE.read_text(encoding="utf-8"), law_fallback="BUrlG")
    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.law == "BUrlG"
    assert chunk.paragraph == "3"
    assert chunk.locator == "BUrlG § 3"
    assert chunk.title == "Dauer des Urlaubs"
    assert "24" in chunk.text
