# Labour-law RAG FastAPI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a small FastAPI app that answers questions only from 12 official German labour-law XML texts, with citations, a refusal path, one HTML page, pytest without a live Gemini key, and Docker.

**Architecture:** Parse gesetze-im-internet XML into paragraph chunks, embed with Gemini, store in local Chroma, retrieve top-k, then ask Gemini for JSON `{answer, refused}`. HTTP handlers never trigger ingest. Tests inject fake embeddings and a fake chat client.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic, ChromaDB, google-genai, httpx, pytest, Docker.

## Global Constraints

- README language: German; all code comments, pytest names, logs, and stdout: English.
- JSON API keys: `snake_case`.
- Collection name: `labour_law`. Persist path: `data/indexes/chroma/` (gitignored).
- Embedding model default: `gemini-embedding-001` (`GEMINI_EMBEDDING_MODEL`). Chat model default: `gemini-2.0-flash` (`GEMINI_CHAT_MODEL`).
- `k=5` neighbours, or fewer if the collection has fewer chunks; never pad with empty sources.
- Do not call the live Gemini API in pytest. Do not commit `.env` or Chroma data.
- Do not add LangChain, auth, agents, web search, or browser-triggered ingest.
- Chat completions must request JSON `{ "answer": string, "refused": boolean }`.
- HTTP 503 `detail` strings (verbatim): `The document index is empty. Run ingest first.` and `The language model is currently unavailable`.
- Disclaimer on the HTML page (verbatim German): `Keine Rechtsberatung.` plus one sentence that answers come only from the loaded federal labour-law texts.

---

## File map

| Path | Responsibility |
| --- | --- |
| `pyproject.toml` | Project metadata, dependencies, pytest config |
| `.env.example` | `GEMINI_API_KEY`, `GEMINI_EMBEDDING_MODEL`, `GEMINI_CHAT_MODEL` |
| `app/__init__.py` | Empty package marker |
| `app/laws.py` | Tuple of 12 abbreviations |
| `app/config.py` | Settings from env |
| `app/schemas.py` | Pydantic request/response models |
| `app/parse_xml.py` | XML → `Chunk` list + splitting |
| `app/embeddings.py` | `EmbeddingClient` protocol + Gemini implementation |
| `app/chat.py` | `ChatClient` protocol + Gemini JSON implementation |
| `app/retrieve.py` | Chroma index build/query/stats |
| `app/answer.py` | Prompt assembly + `answer_question()` |
| `app/ingest.py` | Download zips, parse, embed, persist; `python -m app.ingest` |
| `app/main.py` | FastAPI routes and template |
| `templates/index.html` | Single page UI |
| `tests/fixtures/burlg_mini.xml` | Tiny BUrlG-like XML |
| `tests/conftest.py` | Shared fakes and temp Chroma |
| `tests/test_parse.py` | Parser and splitter |
| `tests/test_retrieve.py` | Ranking with fake vectors |
| `tests/test_ask.py` | HTTP ask/health/stats |
| `tests/test_ingest.py` | Failed download exits non-zero |
| `Dockerfile` | API image |
| `docker-compose.yml` | API + volume |
| `README.md` | German recruiter README |

---

### Task 1: Parser for one paragraph

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/laws.py`
- Create: `app/parse_xml.py`
- Create: `tests/fixtures/burlg_mini.xml`
- Create: `tests/test_parse.py`

**Interfaces:**
- Consumes: raw XML `str`
- Produces: `Chunk(law: str, paragraph: str, locator: str, title: str, text: str)` and `parse_law_xml(xml_text: str, law_fallback: str) -> list[Chunk]`

- [ ] **Step 1: Write the fixture and failing test**

`tests/fixtures/burlg_mini.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dokumente>
  <norm>
    <metadaten>
      <jurabk>BUrlG</jurabk>
      <enbez>§ 3</enbez>
      <titel>Dauer des Urlaubs</titel>
    </metadaten>
    <textdaten>
      <text>
        <Content>
          <P>Der Urlaub beträgt jährlich mindestens 24 Werktage.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
  <norm>
    <metadaten>
      <jurabk>BUrlG</jurabk>
      <enbez>Inhaltsübersicht</enbez>
    </metadaten>
    <textdaten>
      <text>
        <Content>
          <P>This is a table of contents, not a paragraph.</P>
        </Content>
      </text>
    </textdaten>
  </norm>
</dokumente>
```

`tests/test_parse.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_parse.py::test_parse_burlg_paragraph_three -v`

Expected: FAIL with import error or `parse_law_xml` not found.

- [ ] **Step 3: Write minimal implementation**

`pyproject.toml`:

```toml
[project]
name = "rag-fastapi"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "jinja2>=3.1.0",
  "python-dotenv>=1.0.0",
  "pydantic-settings>=2.6.0",
  "httpx>=0.27.0",
  "chromadb>=0.5.0",
  "google-genai>=1.0.0",
]

[dependency-groups]
dev = ["pytest>=8.0.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`app/laws.py`:

```python
LAW_ABBREVIATIONS: tuple[str, ...] = (
    "ArbZG",
    "BUrlG",
    "KSchG",
    "TzBfG",
    "EntgFG",
    "NachwG",
    "MiLoG",
    "AGG",
    "MuSchG",
    "JArbSchG",
    "BEEG",
    "ArbSchG",
)
```

`app/parse_xml.py`: implement `Chunk` as a frozen dataclass and `parse_law_xml` using `xml.etree.ElementTree`. Ignore XML namespaces by using `tag.split("}")[-1]` as the local name. For each `norm`:

- Read `jurabk` (else `law_fallback`), `enbez`, `titel`.
- Keep the norm only when `enbez` matches `^§\s*([0-9]+[a-z]?)` (case-insensitive). `paragraph` is the captured number (`3`, `3a`).
- `locator` is `f"{law} § {paragraph}"`.
- `text` is all descendant text of `textdaten`, whitespace-collapsed.
- Skip norms with empty text.

Create empty `app/__init__.py`.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `pytest tests/test_parse.py::test_parse_burlg_paragraph_three -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app/__init__.py app/laws.py app/parse_xml.py tests/fixtures/burlg_mini.xml tests/test_parse.py
git commit -m "Add labour-law XML parser for paragraph chunks."
```

---

### Task 2: Split oversized paragraphs

**Files:**
- Modify: `app/parse_xml.py`
- Modify: `tests/test_parse.py`

**Interfaces:**
- Consumes: `Chunk` from Task 1
- Produces: `split_chunks(chunks: list[Chunk], max_chars: int = 6000, overlap: int = 200) -> list[Chunk]` used by ingest after parse. Absatz detection: numbered prefixes `(1)` / `(2)` at line starts, or `Absatz` metadata if present in the fixture as separate `<P>` tags starting with `(n)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_parse.py`:

```python
from app.parse_xml import Chunk, split_chunks


def test_split_on_absatz_when_over_limit():
    text = "(1) " + ("aaaa " * 800) + "\n(2) " + ("bbbb " * 800)
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="", text=text)
    parts = split_chunks([chunk], max_chars=1000, overlap=20)
    assert len(parts) == 2
    assert parts[0].locator == "BUrlG § 3 Abs. 1"
    assert parts[1].locator == "BUrlG § 3 Abs. 2"
    assert parts[0].paragraph == "3"
    assert parts[1].paragraph == "3"


def test_split_windows_when_absatz_still_too_long():
    text = "x" * 2500
    chunk = Chunk(law="BUrlG", paragraph="3", locator="BUrlG § 3", title="", text=text)
    parts = split_chunks([chunk], max_chars=1000, overlap=200)
    assert len(parts) == 3
    assert parts[0].locator == "BUrlG § 3 (part 1)"
    assert parts[1].locator == "BUrlG § 3 (part 2)"
    assert parts[2].locator == "BUrlG § 3 (part 3)"
    assert parts[1].text.startswith(parts[0].text[-200:])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_parse.py -v`

Expected: FAIL on `split_chunks` not defined.

- [ ] **Step 3: Write minimal implementation**

Implement `split_chunks`:

- If `len(chunk.text) <= max_chars`, keep as-is.
- Else split text into Absätze with regex `(?m)(?=^\(\d+\))`. If that yields 2+ parts and each part’s first match is `(n)`, emit locators `Abs. n`.
- Any piece still `> max_chars`: sliding windows of `max_chars` with `overlap`. Locator `f"{law} § {paragraph} (part {i})"` 1-based. Overlap: next window starts at `max_chars - overlap`.
- If Absätze exist but only one is oversized, split only that piece with windows; locators for unsplit Absätze stay `Abs. n`.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `pytest tests/test_parse.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/parse_xml.py tests/test_parse.py
git commit -m "Split long statute paragraphs for embedding limits."
```

---

### Task 3: Retrieval with fake embeddings

**Files:**
- Create: `app/config.py`
- Create: `app/embeddings.py`
- Create: `app/retrieve.py`
- Create: `tests/conftest.py`
- Create: `tests/test_retrieve.py`

**Interfaces:**
- Consumes: `Chunk` list; `EmbeddingClient.embed_documents(texts: list[str]) -> list[list[float]]`; `embed_query(text: str) -> list[float]`
- Produces: `IndexStats(laws: int, chunks: int, characters: int, collection: str)`  
  `open_collection(path: Path, embedding_client: EmbeddingClient)`  
  `replace_chunks(collection, chunks: list[Chunk], embedding_client: EmbeddingClient) -> None`  
  `query_chunks(collection, question: str, embedding_client: EmbeddingClient, k: int = 5) -> list[Chunk]`  
  `collection_stats(collection) -> IndexStats`  
  Collection name constant `COLLECTION_NAME = "labour_law"`. Chroma space: cosine.

- [ ] **Step 1: Write the failing test and fake embedder**

`app/embeddings.py` protocol only in this step is fine if the test imports it; if import fails, that is the expected first failure.

`tests/conftest.py`:

```python
from app.embeddings import EmbeddingClient
from app.parse_xml import Chunk


class KeywordEmbeddingClient:
    """Deterministic 2-D vectors for tests. No network."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        lowered = text.lower()
        if "urlaub" in lowered or "leave" in lowered:
            return [1.0, 0.0]
        return [0.0, 1.0]


def leave_chunk() -> Chunk:
    return Chunk(
        law="BUrlG",
        paragraph="3",
        locator="BUrlG § 3",
        title="Dauer des Urlaubs",
        text="Der Urlaub beträgt jährlich mindestens 24 Werktage.",
    )


def wage_chunk() -> Chunk:
    return Chunk(
        law="MiLoG",
        paragraph="1",
        locator="MiLoG § 1",
        title="",
        text="Dieses Gesetz regelt den allgemeinen Mindestlohn.",
    )
```

If `EmbeddingClient` is a `typing.Protocol`, `KeywordEmbeddingClient` needs no inheritance. Keep the protocol in `app/embeddings.py`.

`tests/test_retrieve.py`:

```python
from pathlib import Path

from tests.conftest import KeywordEmbeddingClient, leave_chunk, wage_chunk
from app.retrieve import collection_stats, open_collection, query_chunks, replace_chunks


def test_leave_question_ranks_leave_chunk_first(tmp_path: Path):
    client = KeywordEmbeddingClient()
    collection = open_collection(tmp_path / "chroma", client)
    replace_chunks(collection, [wage_chunk(), leave_chunk()], client)
    hits = query_chunks(collection, "Wie viele Urlaubstage stehen gesetzlich mindestens zu?", client, k=5)
    assert hits[0].locator == "BUrlG § 3"
    stats = collection_stats(collection)
    assert stats.chunks == 2
    assert stats.laws == 2
    assert stats.characters == len(wage_chunk().text) + len(leave_chunk().text)
    assert stats.collection == "labour_law"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieve.py::test_leave_question_ranks_leave_chunk_first -v`

Expected: FAIL with `app.retrieve` missing.

- [ ] **Step 3: Write minimal implementation**

`app/config.py`: `Settings` with `chroma_path: Path = Path("data/indexes/chroma")` via pydantic-settings, extra env fields for Gemini can wait until Task 6 but adding them now avoids a second settings class:

```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_chat_model: str = "gemini-2.0-flash"
    chroma_path: Path = Path("data/indexes/chroma")
```

`app/embeddings.py`:

```python
from typing import Protocol


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
```

`app/retrieve.py`:

- Use `chromadb.PersistentClient(path=str(path))`.
- Custom `chromadb.EmbeddingFunction` that calls `embedding_client.embed_documents` for documents and `embed_query` for queries. Chroma v0.5 `EmbeddingFunction` `__call__(self, input)` receives documents; for queries Chroma may call the same with the query text list — implement `__call__` as embedding each string via `embed_query` so documents and queries share the fake geometry.
- `replace_chunks`: `get_or_create_collection(name="labour_law", metadata={"hnsw:space": "cosine"})`, then `delete_collection` + `create_collection` so re-ingest does not merge. IDs: `f"{law}-{paragraph}-{i}"`.
- Metadata values must be strings/ints; store `law`, `paragraph`, `locator`, `title`; document = `text`.
- `query_chunks`: `n_results=min(k, count)` where `count = collection.count()`. Rebuild `Chunk` from metadatas + documents.
- `collection_stats`: unique `law` values, `count()`, sum of document lengths. If collection missing or count 0: `IndexStats(0, 0, 0, "labour_law")`.

- [ ] **Step 4: Run tests and make sure they pass**

Run: `pytest tests/test_retrieve.py tests/test_parse.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py app/embeddings.py app/retrieve.py tests/conftest.py tests/test_retrieve.py
git commit -m "Index chunks in Chroma and rank with injectable embeddings."
```

---

### Task 4: Ask API with mocked chat

**Files:**
- Create: `app/schemas.py`
- Create: `app/chat.py`
- Create: `app/answer.py`
- Create: `app/main.py`
- Create: `tests/test_ask.py`

**Interfaces:**
- Consumes: `query_chunks`, `ChatClient.complete(system: str, user: str) -> ChatResult(answer: str, refused: bool)`
- Produces: FastAPI app `create_app(embedding_client, chat_client, chroma_path) -> FastAPI` so tests inject fakes. Routes: `GET /health`, `GET /stats`, `POST /ask`.

- [ ] **Step 1: Write failing HTTP tests**

`tests/test_ask.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ask.py -v`

Expected: FAIL with `create_app` missing.

- [ ] **Step 3: Write minimal implementation**

`app/chat.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatResult:
    answer: str
    refused: bool


class ChatClient(Protocol):
    def complete(self, system: str, user: str) -> ChatResult: ...
```

`app/schemas.py`: pydantic `AskRequest(question: str)`, `Source(law, paragraph, locator, snippet)`, `AskResponse(answer, refused, sources: list[Source])`, `HealthResponse`, `StatsResponse`.

`app/answer.py`:

```python
SYSTEM_PROMPT = """You answer questions using only the statute excerpts in the user message.
Reply in the same language as the question.
If the excerpts are insufficient, say that the loaded documents do not contain the answer.
Do not invent figures, company facts, or legal results.
Do not invent citations.
Return JSON only.
"""

def build_user_prompt(question: str, chunks: list[Chunk]) -> str: ...
def answer_question(question, chunks, chat_client) -> ChatResult: ...
```

User prompt lists each chunk as `Locator: ...\nText: ...`. `answer_question` calls `chat_client.complete`.

`app/main.py` `create_app(...)`:

- `GET /health` → `{"status": "ok"}`.
- `GET /stats` → `collection_stats` with zeros if the path has no collection.
- `POST /ask`: strip question; 400 if empty or `len > 2000` (`HTTPException`). If stats.chunks == 0 → 503 empty-index detail. Else retrieve, map sources with snippet = `text[:240]`, call `answer_question`. If `ChatClient.complete` raises, 503 model-unavailable detail.

Module-level `app = create_app(...)` for uvicorn may wait until Task 6 when real clients exist; for now `create_app` is enough if tests never import a default Gemini client. Add a default factory that uses fakes only when `GEMINI_API_KEY` is empty **do not do that** (would surprise production). Instead: `app/main.py` defines `create_app`; `if __name__` not needed. Uvicorn target in later task: a `app` built in Task 6.

For this task, also export `app = create_app(KeywordEmbeddingClient(), FakeChat(), Settings().chroma_path)` — **no**, tests would then depend on fakes in production. Leave `app` unset until Gemini clients exist. Pytest only uses `create_app`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py app/chat.py app/answer.py app/main.py tests/test_ask.py
git commit -m "Expose health, stats, and grounded ask endpoints."
```

---

### Task 5: HTML question page

**Files:**
- Create: `templates/index.html`
- Modify: `app/main.py`
- Modify: `tests/test_ask.py`

**Interfaces:**
- Consumes: FastAPI `Jinja2Templates`
- Produces: `GET /` HTML

- [ ] **Step 1: Write failing test**

```python
def test_home_page_has_disclaimer(tmp_path: Path):
    client = _client(tmp_path, with_chunks=True)
    response = client.get("/")
    assert response.status_code == 200
    assert "Keine Rechtsberatung." in response.text
    assert "question" in response.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ask.py::test_home_page_has_disclaimer -v`

Expected: FAIL 404

- [ ] **Step 3: Write template and route**

`templates/index.html`: German UI labels (`Frage`, `Fragen`, `Antwort`, `Quellen`). Disclaimer: `Keine Rechtsberatung. Antworten stützen sich nur auf die geladenen Bundesgesetze zum Arbeitsrecht.` One `<textarea>`, one button, `<pre>` or `<div id="answer">`, `<ul id="sources">`. Inline CSS is allowed (no extra CSS file required). Script: `fetch("/ask", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({question})})`. On 400/503 show `detail`; for 503 empty index, German display text `Der Dokumentenindex ist leer.` For model unavailable, German `Das Sprachmodell ist gerade nicht erreichbar.` On 200 render `answer`, `refused`, and each `locator`.

`GET /` returns `templates.TemplateResponse("index.html", {"request": request})`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ask.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/index.html app/main.py tests/test_ask.py
git commit -m "Add a single HTML page for asking the labour-law index."
```

---

### Task 6: Ingest CLI and live Gemini adapters

**Files:**
- Create: `.env.example`
- Create: `app/ingest.py`
- Modify: `app/embeddings.py` (add `GeminiEmbeddingClient`)
- Modify: `app/chat.py` (add `GeminiChatClient`)
- Modify: `app/main.py` (module-level `app` for uvicorn)
- Create: `tests/test_ingest.py`

**Interfaces:**
- Consumes: `LAW_ABBREVIATIONS`, `parse_law_xml`, `split_chunks`, `replace_chunks`
- Produces: `download_law_xml(abbreviation: str, http: httpx.Client) -> str`  
  `ingest_all(...)`  
  `python -m app.ingest` exit 1 if any law fails, printing `Failed to ingest {abbreviation}: {reason}` to stderr. On success print `laws={n} chunks={n} characters={n}`.  
  URL: `https://www.gesetze-im-internet.de/{abbreviation.lower()}/xml.zip` — unzip the single `.xml` member.

- [ ] **Step 1: Write failing ingest tests (no network)**

```python
import httpx
import pytest

from app.ingest import download_law_xml, ingest_all


def test_download_failure_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(RuntimeError, match="BUrlG"):
        download_law_xml("BUrlG", client)


def test_ingest_all_stops_on_first_failure(tmp_path, monkeypatch):
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
```

Adjust `ingest_all` signature so the SystemExit test can pass without embeddings: if `download_law_xml` raises, catch, print to stderr, `raise SystemExit(1)` before embedding. `embedding_client=None` is acceptable in this test because the function must exit before using it.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingest.py -v`

Expected: FAIL missing module.

- [ ] **Step 3: Implement download, Gemini clients, CLI, default app**

`download_law_xml`: GET zip, `raise RuntimeError(f"Failed to ingest {abbreviation}: HTTP {status}")` on non-200; zipfile in memory; decode UTF-8 XML.

`GeminiEmbeddingClient`: `google.genai.Client(api_key=...)`, `models.embed_content(model=..., contents=text)`. Embed documents sequentially with a 0.4s sleep between calls to stay inside the free quota. Retry HTTP 429 up to 5 times with 5s backoff. `embed_query` is one `embed_content`.

`GeminiChatClient.complete`: `generate_content` with system instruction `SYSTEM_PROMPT` from `app.answer`, user text, `response_mime_type="application/json"`. Parse JSON to `ChatResult`. On API errors raise a generic `RuntimeError` that `main.py` already turns into 503.

`.env.example`:

```
GEMINI_API_KEY=
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_CHAT_MODEL=gemini-2.0-flash
```

`app/ingest.py` `__main__`: load dotenv, require non-empty `GEMINI_API_KEY` or `sys.exit(1)` with `GEMINI_API_KEY is missing`. Then `ingest_all(LAW_ABBREVIATIONS, httpx.Client(timeout=60), GeminiEmbeddingClient(settings), settings.chroma_path)`.

Default FastAPI `app = create_app(GeminiEmbeddingClient(settings), GeminiChatClient(settings), settings.chroma_path)` at module bottom of `app/main.py`. Tests keep calling `create_app` with fakes.

- [ ] **Step 4: Run all tests**

Run: `pytest tests/ -v`

Expected: PASS. Do not run live ingest in this task unless the human explicitly asks and has quota.

- [ ] **Step 5: Commit**

```bash
git add .env.example app/ingest.py app/embeddings.py app/chat.py app/main.py tests/test_ingest.py
git commit -m "Add Gemini ingest CLI and production clients."
```

---

### Task 7: Docker and German README

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `README.md`
- Modify: `.gitignore` only if `data/` is not already ignored (it is via `data/indexes/`).

**Interfaces:** none beyond running the API container.

- [ ] **Step 1: Write a smoke test that the README contains required German phrases**

`tests/test_readme.py`:

```python
from pathlib import Path

README = Path("README.md").read_text(encoding="utf-8")


def test_readme_has_required_sections():
    assert "gesetze-im-internet.de" in README
    assert "Keine Rechtsberatung" in README
    assert "BUrlG" in README
    assert "POST /ask" in README
    assert "python -m app.ingest" in README
    assert "LangChain" in README or "Agenten" in README
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_readme.py -v`

Expected: FAIL (current README is still the English stub).

- [ ] **Step 3: Write Docker files and German README**

`Dockerfile`: `python:3.12-slim`, copy `pyproject.toml` and `app/` `templates/`, `pip install .`, `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

`docker-compose.yml`: service `api`, port `8000:8000`, env_file `.env`, volume `./data/indexes:/app/data/indexes`. Do **not** run ingest as the default command.

`README.md` (German), must include:

- Two-sentence problem: questions over a corpus that you do not stuff into the prompt.
- Source: gesetze-im-internet.de, list of 12 abbreviations.
- Stats placeholders: `Gesetze: (nach dem ersten Ingest eintragen)`, `Abschnitte: …`, `Zeichen: …`.
- Example `POST /ask` for leave and example JSON; example CEO question with `"refused": true`.
- Disclaimer `Keine Rechtsberatung`.
- How to: `.env`, `python -m app.ingest`, `uvicorn app.main:app --reload`, compose up.
- Non-goals: no agents, no login, no cloud vector DB, no LangChain.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml README.md tests/test_readme.py
git commit -m "Document the German labour-law RAG demo and add Docker."
```

---

## Self-review (spec coverage)

| Spec item | Task |
| --- | --- |
| 12 labour laws, official XML | 1 (`laws.py`), 6 (download) |
| Chunk = `§`, metadata, 6000-char split | 1, 2 |
| Ingest fails loudly per law | 6 |
| Chroma path, cosine, `labour_law`, replace not merge | 3 |
| Gemini embedding/chat models + JSON refuse | 6, 4 |
| `k=5`, empty index 503, 400 validation | 4 |
| Sources from retrieval, snippet 240 | 4 |
| Model 503 English detail | 4 |
| HTML disclaimer, no JS framework | 5 |
| CLI ingest, `.env.example` | 6 |
| Tests without live key | 1–6 |
| Docker, German README, non-goals | 7 |
| No website screenshots in first implementation | (omitted on purpose) |
