from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")


def test_readme_has_required_sections():
    assert "gesetze-im-internet.de" in README
    assert "Keine Rechtsberatung" in README
    assert "BUrlG" in README
    assert "POST /ask" in README
    assert "python -m app.ingest" in README
    assert "LangChain" in README or "Agenten" in README
