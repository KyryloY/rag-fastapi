from pathlib import Path
import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.parse_xml import Chunk
from app.retrieve import open_collection, replace_chunks
from tests.conftest import KeywordEmbeddingClient, leave_chunk, wage_chunk


class FakeChat:
    def complete(self, system: str, user: str):
        from app.chat import ChatResult

        if "Siemens" in user or "CEO" in user:
            return ChatResult(
                answer="In den geladenen Dokumenten steht dazu nichts.",
                refused=True,
            )
        return ChatResult(
            answer="Der gesetzliche Mindesturlaub beträgt 24 Werktage (BUrlG).",
            refused=False,
        )


def _client(tmp_path: Path, with_chunks: bool) -> TestClient:
    embeddings = KeywordEmbeddingClient()
    collection = open_collection(tmp_path / "chroma", embeddings)
    if with_chunks:
        replace_chunks(collection, [wage_chunk(), leave_chunk()], embeddings)
    app = create_app(
        embedding_client=embeddings,
        chat_client=FakeChat(),
        chroma_path=tmp_path / "chroma",
    )
    return TestClient(app)


def test_health():
    # chroma path unused for health
    from app.main import create_app
    from tests.conftest import KeywordEmbeddingClient

    app = create_app(
        embedding_client=KeywordEmbeddingClient(),
        chat_client=FakeChat(),
        chroma_path=Path("data/indexes/chroma"),
    )
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_question_is_400(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.post("/ask", json={"question": "   "})
    assert response.status_code == 400


def test_too_long_question_is_400(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.post("/ask", json={"question": "x" * 2001})
    assert response.status_code == 400


def test_empty_index_is_503(tmp_path: Path):
    client = _client(tmp_path, with_chunks=False)
    response = client.post("/ask", json={"question": "Wie viele Urlaubstage?"})
    assert response.status_code == 503
    assert response.json() == {"detail": "The document index is empty. Run ingest first."}


def test_leave_question_returns_sources(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.post(
        "/ask",
        json={"question": "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert "24" in body["answer"]
    assert body["sources"][0]["locator"] == "BUrlG § 3"
    assert body["sources"][0]["law"] == "BUrlG"
    assert body["sources"][0]["paragraph"] == "3"
    assert body["sources"][0]["snippet"].startswith("Der Urlaub")


def test_home_page_has_disclaimer(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.get("/")
    assert response.status_code == 200
    assert "Keine Rechtsberatung." in response.text
    assert "question" in response.text.lower()


def test_ceo_salary_is_refused(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.post(
        "/ask",
        json={"question": "Wie hoch ist das Gehalt des CEOs von Siemens?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is True
    assert not re.search(r"\d{3,}", body["answer"])
    assert body["sources"]
    assert body["sources"][0]["locator"]


def test_ask_does_not_load_full_collection_stats(tmp_path: Path, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("collection_stats should not run on POST /ask")

    monkeypatch.setattr("app.main.collection_stats", boom)
    client = _client(tmp_path, with_chunks=True)
    response = client.post(
        "/ask",
        json={"question": "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"},
    )
    assert response.status_code == 200


def test_chat_runtime_error_is_503(tmp_path: Path):
    class BoomChat:
        def complete(self, system: str, user: str):
            raise RuntimeError("The language model is currently unavailable")

    embeddings = KeywordEmbeddingClient()
    chroma_path = tmp_path / "chroma"
    replace_chunks(
        open_collection(chroma_path, embeddings),
        [wage_chunk(), leave_chunk()],
        embeddings,
    )
    app = create_app(
        embedding_client=embeddings,
        chat_client=BoomChat(),
        chroma_path=chroma_path,
    )
    response = TestClient(app).post(
        "/ask",
        json={"question": "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"},
    )
    assert response.status_code == 503
    assert response.json() == {
        "detail": "The language model is currently unavailable"
    }
