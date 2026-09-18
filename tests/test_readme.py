from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")


def test_readme_has_required_sections():
    assert "gesetze-im-internet.de" in README
    assert "Keine Rechtsberatung" in README
    assert "BUrlG" in README
    assert "POST /ask" in README
    assert "python -m app.ingest" in README
    assert "LangChain" in README or "Agenten" in README
    assert "uvicorn app.main:create_default_app --factory" in README
    refused_block = README.split("Gehalt des CEOs von Siemens")[1]
    assert '"refused": true' in refused_block
    assert '"sources": []' not in refused_block
    assert '"locator"' in refused_block
