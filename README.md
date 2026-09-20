# Arbeitsrecht-RAG (FastAPI)

Fragen zu einem festen Korpus deutscher Bundesgesetze lassen sich nicht zuverlässig beantworten, wenn man den gesamten Text in den Prompt packt — Kontextfenster und Halluzinationen setzen Grenzen. Dieses Demo-Projekt lädt offizielle Gesetzestexte, indiziert sie lokal und beantwortet Nutzerfragen per Retrieval-Augmented Generation (RAG) mit Quellenangaben.

**Keine Rechtsberatung.** Antworten stützen sich nur auf die geladenen Dokumente; sie ersetzen keine anwaltliche Beratung.

## Datenquelle

Texte werden von [gesetze-im-internet.de](https://www.gesetze-im-internet.de/) als XML bezogen. Im Index sind derzeit diese zwölf Abkürzungen vorgesehen:

`ArbZG`, `BUrlG`, `KSchG`, `TzBfG`, `EntgFG`, `NachwG`, `MiLoG`, `AGG`, `MuSchG`, `JArbSchG`, `BEEG`, `ArbSchG`

Nach dem Ingest mit Absatz-Chunks (Stand 2026-09-19):

- **Gesetze:** 12
- **Abschnitte:** 968 (meist ein Absatz je Abschnitt)
- **Zeichen:** 447554

## API-Beispiel: `POST /ask`

Urlaubsfrage (Antwort aus dem Index):

```http
POST /ask
Content-Type: application/json

{"question": "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"}
```

Beispielantwort (Schema; Inhalt hängt vom Modell ab):

```json
{
  "answer": "Der gesetzliche Mindesturlaub beträgt 24 Werktage (BUrlG).",
  "refused": false,
  "sources": [
    {
      "law": "BUrlG",
      "paragraph": "3",
      "locator": "BUrlG § 3 Abs. 1",
      "title": "Dauer des Urlaubs",
      "snippet": "(1) Der Urlaub beträgt jährlich mindestens 24 Werktage."
    }
  ]
}
```

Frage außerhalb des Korpus (Modell lehnt ab, keine erfundenen Fakten und keine Quellenliste):

```http
POST /ask
Content-Type: application/json

{"question": "Wie hoch ist das Gehalt des CEOs von Siemens?"}
```

```json
{
  "answer": "In den geladenen Dokumenten steht dazu nichts.",
  "refused": true,
  "sources": []
}
```

Weitere Endpunkte: `GET /health`, `GET /` (einfache HTML-Oberfläche auf Deutsch).

## Einrichtung und Betrieb

1. **Umgebung:** `.env` aus `.env.example` anlegen und `GEMINI_API_KEY` setzen (Embedding- und Chat-Modelle optional überschreiben).
2. **Index aufbauen:** `python -m app.ingest` — lädt alle Gesetze, erzeugt Embeddings über Gemini und schreibt Chroma unter `data/indexes/chroma`.
3. **Lokal starten:** `uvicorn app.main:create_default_app --factory --reload` — API unter `http://127.0.0.1:8000`.
4. **Docker:** `docker compose up --build` — startet nur die API; der Index liegt im Volume `./data/indexes`. Ingest vor dem ersten Start separat auf dem Host ausführen oder einmalig im Container: `docker compose run --rm api python -m app.ingest`.

Ohne Index antwortet `POST /ask` mit HTTP 503 (Index leer).

## Technik (kurz)

FastAPI, Chroma (lokal, Cosine), Google Gemini für Embeddings und Chat, Lingua zur Erkennung von Deutsch/Englisch in der Frage (bei Abweichung in der Antwort ein Wiederholungsversuch), Jinja2-Template ohne JS-Framework.

## Bewusst nicht im Scope

- Keine autonomen **Agenten** oder Tool-Schleifen
- Kein Login / keine Mandantenfähigkeit
- Keine Cloud-Vektor-Datenbank (nur lokales Chroma)
- Kein **LangChain** — schlanke, nachvollziehbare Python-Pipeline
