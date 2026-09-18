# RAG FastAPI: German labour-law Q&A

Date: 2026-09-18  
Status: approved in conversation; awaiting user review of this file

## Purpose

A small portfolio demo: a FastAPI backend that answers questions **only** from a fixed pack of official German labour-law texts. Retrieval uses embeddings; the language model sees a handful of paragraphs, not the whole corpus. The public story is “backends and APIs for generative AI with embeddings”, not a chatbot and not a law firm.

This is not legal advice. The UI and the German README must say so in one short sentence.

## Non-goals

- Login, users, conversation history stored in a database
- Agents, tool calling, web search, or answers from the open internet
- LangChain or similar orchestration frameworks
- Cloud vector databases
- neoLab / employer texts, personal data, or the project articles from kyryloyasko.de as the corpus
- Ingest triggered from the browser (would hammer gesetze-im-internet.de and the free Gemini quota)
- Paying for Gemini; use the existing free quota only
- Pretending the recruiter will run the app; README and a later case-study article carry screenshots and example JSON

## Corpus

Source: XML exports from [gesetze-im-internet.de](https://www.gesetze-im-internet.de/) (official federal law texts).

Fixed list of abbreviations (ingest URLs: `https://www.gesetze-im-internet.de/{slug}/xml.zip`, slug is the lowercase abbreviation):

| Abbreviation | Role in the demo |
| --- | --- |
| ArbZG | Working time |
| BUrlG | Statutory leave |
| KSchG | Dismissal protection |
| TzBfG | Part-time and fixed-term work |
| EntgFG | Continued pay during illness |
| NachwG | Written statement of conditions |
| MiLoG | Minimum wage |
| AGG | Equal treatment |
| MuSchG | Maternity protection |
| JArbSchG | Young workers |
| BEEG | Parental leave / Elterngeld |
| ArbSchG | Occupational safety |

Do not download the full federal catalogue. After ingest, `GET /stats` and the README must report three integers computed from the index: number of laws present, number of chunks, total characters stored.

## Chunking

- Default unit: one statute paragraph (`§`) = one chunk.
- Chunk metadata (all required): `law` (e.g. `BUrlG`), `paragraph` (the § number as in the XML, e.g. `3` or `3a`), `locator` (display string `BUrlG § 3`), `title` (paragraph heading if present, else empty string).
- If a single paragraph’s plain text is longer than 6 000 characters, split on `Absatz` boundaries; if one Absatz still exceeds 6 000 characters, split on 6 000-character windows with 200-character overlap. Every sub-chunk keeps the same `law` and `paragraph`; `locator` becomes `BUrlG § 3 Abs. 2` when an Absatz number exists, otherwise `BUrlG § 3 (part 2)`.
- Do not silently skip a law if download or parse fails: ingest exits with a non-zero status and prints the abbreviation that failed.

## Index

- Local Chroma persisted under `data/indexes/chroma/` (gitignored).
- Embedding model: `gemini-embedding-001`, overridable via `GEMINI_EMBEDDING_MODEL`.
- Distance: cosine.
- Collection name: `labour_law`.
- Re-ingest replaces the collection; it does not merge with a stale index.

## Question answering

1. Reject empty or whitespace-only `question` with HTTP 400. Reject `question` longer than 2 000 characters with HTTP 400.
2. Embed the question with the same embedding model as ingest.
3. Query Chroma for `k=5` chunks.
4. Call the chat model with those five texts and locators. The system prompt (English in code) must require:
   - answer in the language of the question (typically German);
   - use only the provided excerpts;
   - if the excerpts are insufficient, say that the loaded documents do not contain the answer and do not invent a figure, company fact, or legal result;
   - do not invent citations; the API will attach the retrieved locators itself.
5. Chat model: `gemini-3.5-flash-lite`, overridable via `GEMINI_CHAT_MODEL`. The chat call must request JSON (schema or JSON mime type), not free prose. Shape:

```json
{"answer": "string", "refused": true}
```

`refused` is `true` only when the excerpts do not contain the answer. The HTTP body copies these two fields and adds `sources` from retrieval. Do not parse German sentences to guess refusal.
6. Do not add a similarity cutoff that skips the model. Retrieval always returns five neighbours when the index is non-empty. If the index has zero chunks, `POST /ask` returns HTTP 503 with `{"detail": "The document index is empty. Run ingest first."}`.

Out-of-corpus example that must refuse: a question about a named company’s CEO salary.

In-corpus example that must cite: statutory minimum annual leave under BUrlG.

## HTTP API

Base application: FastAPI. JSON keys are `snake_case`.

### `GET /health`

`200` and `{"status": "ok"}`.

### `GET /stats`

`200` when the index exists:

Empty index (missing folder or zero chunks):

```json
{
  "laws": 0,
  "chunks": 0,
  "characters": 0,
  "collection": "labour_law"
}
```

After ingest, the three numbers come from stored documents, not from counting the abbreviation list in code. The HTML page may load with zeros; `POST /ask` returns 503 until at least one chunk exists.

### `POST /ask`

Request:

```json
{"question": "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"}
```

Success `200`:

```json
{
  "answer": "…",
  "refused": false,
  "sources": [
    {
      "law": "BUrlG",
      "paragraph": "3",
      "locator": "BUrlG § 3",
      "snippet": "first ~240 characters of the chunk"
    }
  ]
}
```

`sources` is the retrieval list (the five neighbours), not a second model-guessed bibliography. `snippet` is truncated plain text for display.

Gemini / network failure: HTTP 503, body `{"detail": "The language model is currently unavailable"}` (English in the JSON `detail` field; the HTML page shows a German sentence for the same condition).

## User interface

- `GET /` serves one HTML page from a FastAPI template: question field, submit button, answer area, source list, disclaimer in German (`Keine Rechtsberatung.` plus one sentence that answers come only from the loaded federal labour-law texts).
- No JavaScript framework. One small script to `POST /ask` and render JSON is allowed.
- No chat transcript, no streaming requirement.

## CLI ingest

Entry point: `python -m app.ingest` (or equivalent documented in the README).

Requires `GEMINI_API_KEY` in the environment (from `.env` locally; never committed). `.env.example` lists `GEMINI_API_KEY`, `GEMINI_EMBEDDING_MODEL`, `GEMINI_CHAT_MODEL` without secrets.

Ingest downloads each zip, parses XML to chunks, embeds, and persists Chroma. It prints the three stats at the end (English stdout).

## Layout

```
app/
  __init__.py
  main.py          # FastAPI app, mounts routes and templates
  config.py
  laws.py          # the 12 abbreviations
  ingest.py        # download, parse, embed, persist
  parse_xml.py     # gesetze-im-internet XML → chunks
  retrieve.py
  answer.py        # prompt + Gemini chat
  schemas.py       # pydantic models
templates/index.html
static/            # only if needed for one CSS file
tests/
  fixtures/        # tiny BUrlG-like XML
  test_parse.py
  test_retrieve.py
  test_ask.py
docs/superpowers/specs/  # this file
```

Comments, logs, pytest names, and stdout: English. README: German.

## Tests (CI, no live Gemini)

- Parser: fixture XML with a § 3 whose text states a 24-day minimum; expect locator `BUrlG § 3` and the number 24 in the chunk text.
- Retrieval: build an in-memory or temp-dir index with that one chunk using **fake embeddings** (deterministic vectors in the test double). A leave question must rank that chunk first. Do not call Gemini in CI.
- Ask path: mock the chat client. CEO-salary question → `refused` is true and the answer does not contain a salary number. Empty question → 400.
- No test requires `GEMINI_API_KEY`.

## Docker

A `Dockerfile` plus `docker-compose.yml` that runs the API and mounts `data/indexes` as a volume. Compose does not run ingest by default (ingest needs a key and network). README explains: set the key, run ingest once, then start the API.

## README (German)

Must include: problem in two sentences; official source of texts; the 12 abbreviations; the three stats placeholders to fill after the first real ingest; example `POST /ask` and example JSON (in-corpus and refused); disclaimer; how to ingest and run; explicit non-goals; link to this spec is optional and not required for recruiters.

## Constraints already decided

- Recruiter will likely only read the repo and the later website case study.
- Screenshots for the website are produced after the app works; they are not part of the first implementation commit.
- Stack: Python, FastAPI, Chroma, Gemini embeddings + Gemini chat, pytest, Docker.
- Timebox is “small demo”; do not add features beyond this spec.
