"""Run a documented query series against the live labour-law index.

Writes a German markdown report for the later portfolio case study.
Does not print the API key.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.answer import answer_question
from app.chat import GeminiChatClient
from app.config import Settings
from app.embeddings import GeminiEmbeddingClient
from app.retrieve import collection_stats, open_collection, query_chunks

REPORT_PATH = Path("docs/experiments/2026-09-18-query-series.md")


@dataclass(frozen=True)
class Case:
    case_id: str
    kind: str
    language: str
    question: str
    expectation: str


CASES: list[Case] = [
    Case(
        "T1",
        "in-corpus",
        "de",
        "Wie viele Urlaubstage stehen gesetzlich mindestens zu?",
        "Should cite BUrlG § 3: at least 24 Werktage. refused=false.",
    ),
    Case(
        "T2",
        "in-corpus",
        "de",
        "Wie lang darf die regelmäßige werktägliche Arbeitszeit nach dem Arbeitszeitgesetz höchstens sein?",
        "Should cite ArbZG § 3: eight hours. refused=false.",
    ),
    Case(
        "T3",
        "in-corpus",
        "de",
        "Wie lange muss das Entgelt bei Krankheit mindestens fortgezahlt werden?",
        "Should cite EntgFG (six weeks). refused=false.",
    ),
    Case(
        "T4",
        "in-corpus",
        "de",
        "Ab welcher Betriebsgröße gilt das Kündigungsschutzgesetz grundsätzlich?",
        "Should cite KSchG § 23 (more than ten employees, with nuances). refused=false if the excerpt is found.",
    ),
    Case(
        "T5",
        "in-corpus",
        "de",
        "Was regelt das Nachweisgesetz in einem Satz?",
        "Should summarize NachwG from retrieved paragraphs. refused=false.",
    ),
    Case(
        "F1",
        "out-of-corpus",
        "de",
        "Wie hoch ist das Gehalt des CEOs von Siemens?",
        "Must refuse. No invented euro amount.",
    ),
    Case(
        "F2",
        "out-of-corpus",
        "de",
        "Wie wird das Wetter in Karlsruhe nächste Woche?",
        "Must refuse. Weather is not in the labour-law pack.",
    ),
    Case(
        "F3",
        "out-of-corpus",
        "de",
        "Wie viele Urlaubstage hat man gesetzlich in Frankreich?",
        "Must refuse. French law is not loaded.",
    ),
    Case(
        "F4",
        "out-of-corpus",
        "de",
        "Welche interne Homeoffice-Regel gilt bei neoLab?",
        "Must refuse. Employer policy is not in the corpus.",
    ),
    Case(
        "P1",
        "partially-false",
        "de",
        "Der gesetzliche Mindesturlaub beträgt 30 Tage, stimmt das?",
        "Should not agree with 30. Should correct using BUrlG (24 Werktage) or refuse if unsure.",
    ),
    Case(
        "P2",
        "partially-false",
        "de",
        "Nach dem Bundesurlaubsgesetz habe ich Anspruch auf 24 Wochen Urlaub, oder?",
        "Should reject 24 weeks; the statute speaks of Werktage, not weeks.",
    ),
    Case(
        "P3",
        "partially-false",
        "de",
        "Das Arbeitszeitgesetz erlaubt zwölf Stunden Arbeit an jedem Werktag ohne Pause und ohne Ausnahme. Stimmt das?",
        "Should not accept this as a blanket rule. ArbZG has an 8-hour baseline and rest-break rules.",
    ),
    Case(
        "P4",
        "partially-false",
        "de",
        "Das Mindestlohngesetz legt den Stundenlohn fest auf genau 20 Euro. Ist das so im Gesetzestext?",
        "Should not invent 20 Euro. Either cite the actual MiLoG wording or refuse if the amount is not in the retrieved excerpts.",
    ),
    Case(
        "E1",
        "in-corpus",
        "en",
        "How many statutory annual leave days does German federal law guarantee at minimum?",
        "Answer in English, grounded in BUrlG § 3 (24 Werktage). refused=false.",
    ),
    Case(
        "E2",
        "out-of-corpus",
        "en",
        "What is the salary of the Siemens CEO?",
        "Must refuse, in English.",
    ),
    Case(
        "E3",
        "partially-false",
        "en",
        "German law gives every employee 30 calendar days of vacation. Is that correct?",
        "Should not confirm 30 calendar days. Point to BUrlG 24 Werktage or refuse.",
    ),
    Case(
        "E4",
        "in-corpus",
        "en",
        "According to the Working Time Act, how long is the regular working day?",
        "Should cite ArbZG in English. refused=false if retrieval finds § 3.",
    ),
]


def _md_escape(text: str) -> str:
    return text.replace("\r\n", "\n").strip()


def main() -> None:
    settings = Settings()
    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is missing")

    embeddings = GeminiEmbeddingClient(settings)
    chat = GeminiChatClient(settings)
    collection = open_collection(settings.chroma_path, embeddings)
    stats = collection_stats(collection)
    if stats.chunks == 0:
        raise SystemExit("The document index is empty. Run ingest first.")

    lines: list[str] = [
        "# Query series: labour-law RAG",
        "",
        f"- Date (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        f"- Chat model: `{settings.gemini_chat_model}`",
        f"- Embedding model: `{settings.gemini_embedding_model}`",
        f"- Index: {stats.laws} laws, {stats.chunks} chunks, {stats.characters} characters",
        "- Disclaimer: Keine Rechtsberatung. Rohprotokoll für die Fallstudie.",
        "",
        "## Setup",
        "",
        "Each case runs the same production path: embed the question, retrieve 5 neighbours, ask the chat model for JSON `{answer, refused}`. Sources listed below are the retrieval list, not a second bibliography.",
        "",
    ]

    for case in CASES:
        hits = query_chunks(collection, case.question, embeddings, k=5)
        result = answer_question(case.question, hits, chat)
        locators = ", ".join(chunk.locator for chunk in hits) or "(none)"
        lines.extend(
            [
                f"## {case.case_id} — {case.kind} ({case.language})",
                "",
                f"**Question:** {_md_escape(case.question)}",
                "",
                f"**Expectation:** {_md_escape(case.expectation)}",
                "",
                f"**refused:** `{str(result.refused).lower()}`",
                "",
                f"**Retrieved:** {locators}",
                "",
                "**Answer:**",
                "",
                _md_escape(result.answer),
                "",
            ]
        )
        print(f"{case.case_id} refused={result.refused} hits={len(hits)}", flush=True)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
