from pathlib import Path

from app.parse_xml import Chunk, parse_law_xml, split_chunks


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


def test_split_short_numbered_absatz_always():
    text = (
        "(1) Der Urlaub beträgt jährlich mindestens 24 Werktage."
        "(2) Als Werktage gelten alle Kalendertage, die nicht Sonn- oder gesetzliche Feiertage sind."
    )
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="Dauer des Urlaubs", text=text)
    parts = split_chunks([chunk])
    assert [part.locator for part in parts] == ["BUrlG § 3 Abs. 1", "BUrlG § 3 Abs. 2"]
    assert parts[0].text.startswith("(1)")
    assert "24" in parts[0].text
    assert parts[1].text.startswith("(2)")
    assert "Feiertage" in parts[1].text


def test_split_on_absatz_when_over_limit():
    text = "(1) " + ("aaaa " * 150) + "\n(2) " + ("bbbb " * 150)
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="", text=text)
    parts = split_chunks([chunk], max_chars=1000, overlap=20)
    assert len(parts) == 2
    assert parts[0].locator == "BUrlG § 3 Abs. 1"
    assert parts[1].locator == "BUrlG § 3 Abs. 2"
    assert parts[0].paragraph == "3"
    assert parts[1].paragraph == "3"
    assert len(parts[0].text) <= 1000
    assert len(parts[1].text) <= 1000


def test_split_absatz_mixed_short_and_long():
    text = "(1) short absatz text\n(2) " + ("x" * 2500)
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="", text=text)
    parts = split_chunks([chunk], max_chars=1000, overlap=200)
    assert parts[0].locator == "BUrlG § 3 Abs. 1"
    assert parts[0].text.startswith("(1) short")
    windowed = parts[1:]
    assert len(windowed) == 3
    assert windowed[0].locator == "BUrlG § 3 Abs. 2 (part 1)"
    assert windowed[1].locator == "BUrlG § 3 Abs. 2 (part 2)"
    assert windowed[2].locator == "BUrlG § 3 Abs. 2 (part 3)"
    assert all(len(p.text) <= 1000 for p in windowed)


def test_split_windows_when_absatz_still_too_long():
    text = "x" * 2500
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="", text=text)
    parts = split_chunks([chunk], max_chars=1000, overlap=200)
    assert len(parts) == 3
    assert parts[0].locator == "BUrlG § 3 (part 1)"
    assert parts[1].locator == "BUrlG § 3 (part 2)"
    assert parts[2].locator == "BUrlG § 3 (part 3)"
    assert parts[1].text.startswith(parts[0].text[-200:])


def test_child_text_keeps_nested_xml():
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<dokumente>
  <norm>
    <metadaten>
      <jurabk>BUrlG</jurabk>
      <enbez><NR>§ 3</NR></enbez>
      <titel>Dauer <ABK>des</ABK> Urlaubs</titel>
    </metadaten>
    <textdaten>
      <text>
        <Content>
          <P>Der Urlaub beträgt jährlich mindestens 24 Werktage.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
</dokumente>
"""
    chunks = parse_law_xml(xml_text, law_fallback="BUrlG")
    assert len(chunks) == 1
    assert chunks[0].paragraph == "3"
    assert chunks[0].title == "Dauer des Urlaubs"
