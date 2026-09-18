import io
import zipfile
from pathlib import Path

import httpx
import pytest

from app.ingest import download_law_xml, ingest_all
from app.retrieve import collection_stats, open_collection
from tests.conftest import KeywordEmbeddingClient

FIXTURE = Path(__file__).parent / "fixtures" / "burlg_mini.xml"


def _zip_bytes(member_name: str, xml_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(member_name, xml_text.encode("utf-8"))
    return buffer.getvalue()


def test_download_failure_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(RuntimeError, match="BUrlG"):
        download_law_xml("BUrlG", client)


def test_download_unzips_xml_from_official_url():
    xml_text = FIXTURE.read_text(encoding="utf-8")
    payload = _zip_bytes("burlg.xml", xml_text)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://www.gesetze-im-internet.de/burlg/xml.zip"
        return httpx.Response(200, content=payload, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert download_law_xml("BUrlG", client) == xml_text


def test_ingest_all_stops_on_first_failure(tmp_path, monkeypatch, capsys):
    def boom(abbreviation, http):
        raise RuntimeError(f"Failed to ingest {abbreviation}: 404")

    monkeypatch.setattr("app.ingest.download_law_xml", boom)
    with pytest.raises(SystemExit) as exc:
        ingest_all(
            abbreviations=("BUrlG",),
            http=httpx.Client(),
            embedding_client=None,
            chroma_path=tmp_path,
        )
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Failed to ingest BUrlG:" in captured.err


def test_ingest_all_parses_splits_and_indexes(tmp_path, capsys):
    xml_text = FIXTURE.read_text(encoding="utf-8")
    payload = _zip_bytes("burlg.xml", xml_text)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    embeddings = KeywordEmbeddingClient()
    ingest_all(
        abbreviations=("BUrlG",),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        embedding_client=embeddings,
        chroma_path=tmp_path,
    )
    stats = collection_stats(open_collection(tmp_path, embeddings))
    assert stats.laws == 1
    assert stats.chunks >= 1
    assert stats.characters > 0
    captured = capsys.readouterr()
    assert f"laws={stats.laws}" in captured.out
    assert f"chunks={stats.chunks}" in captured.out
    assert f"characters={stats.characters}" in captured.out


def test_ingest_all_fails_when_law_parses_to_zero_chunks(tmp_path, capsys):
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<dokumente>
  <norm>
    <metadaten>
      <jurabk>BUrlG</jurabk>
      <enbez>Inhaltsübersicht</enbez>
    </metadaten>
    <textdaten>
      <text><Content><P>Table of contents only.</P></Content></text>
    </textdaten>
  </norm>
</dokumente>
"""
    payload = _zip_bytes("burlg.xml", xml_text)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, request=request)

    with pytest.raises(SystemExit) as exc:
        ingest_all(
            abbreviations=("BUrlG",),
            http=httpx.Client(transport=httpx.MockTransport(handler)),
            embedding_client=KeywordEmbeddingClient(),
            chroma_path=tmp_path,
        )
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Failed to ingest BUrlG:" in captured.err
