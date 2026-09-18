# Query series: labour-law RAG

- Date (UTC): 2026-09-18 11:05
- Chat model: `gemini-3.5-flash-lite`
- Embedding model: `gemini-embedding-001`
- Index: 12 laws, 356 chunks, 448775 characters
- Disclaimer: Keine Rechtsberatung. Rohprotokoll für die Fallstudie.

## Setup

Each case runs the same production path: embed the question, retrieve 5 neighbours, ask the chat model for JSON `{answer, refused}`. Sources listed below are the retrieval list, not a second bibliography.

## T1 — in-corpus (de)

**Question:** Wie viele Urlaubstage stehen gesetzlich mindestens zu?

**Expectation:** Should cite BUrlG § 3: at least 24 Werktage. refused=false.

**refused:** `false`

**Retrieved:** BUrlG § 3, BUrlG § 1, JArbSchG § 19, BUrlG § 4, BUrlG § 9

**Answer:**

Der gesetzliche Mindesturlaub beträgt nach § 3 Abs. 1 BUrlG jährlich mindestens 24 Werktage. Für Jugendliche gelten abweichende Regelungen nach § 19 JArbSchG (mindestens 25 bis 30 Werktage je nach Alter).

## T2 — in-corpus (de)

**Question:** Wie lang darf die regelmäßige werktägliche Arbeitszeit nach dem Arbeitszeitgesetz höchstens sein?

**Expectation:** Should cite ArbZG § 3: eight hours. refused=false.

**refused:** `false`

**Retrieved:** ArbZG § 3, JArbSchG § 8, ArbZG § 21a, JArbSchG § 4, JArbSchG § 7

**Answer:**

Nach dem Arbeitszeitgesetz (§ 3 ArbZG) darf die werktägliche Arbeitszeit der Arbeitnehmer acht Stunden nicht überschreiten. Sie kann auf bis zu zehn Stunden nur verlängert werden, wenn innerhalb von sechs Kalendermonaten oder innerhalb von 24 Wochen im Durchschnitt acht Stunden werktäglich nicht überschritten werden.

## T3 — in-corpus (de)

**Question:** Wie lange muss das Entgelt bei Krankheit mindestens fortgezahlt werden?

**Expectation:** Should cite EntgFG (six weeks). refused=false.

**refused:** `false`

**Retrieved:** EntgFG § 3, EntgFG § 4a, BUrlG § 10, EntgFG § 4, EntgFG § 8

**Answer:**

Der Anspruch auf Entgeltfortzahlung im Krankheitsfall durch den Arbeitgeber besteht für die Zeit der Arbeitsunfähigkeit bis zur Dauer von sechs Wochen.

## T4 — in-corpus (de)

**Question:** Ab welcher Betriebsgröße gilt das Kündigungsschutzgesetz grundsätzlich?

**Expectation:** Should cite KSchG § 23 (more than ten employees, with nuances). refused=false if the excerpt is found.

**refused:** `false`

**Retrieved:** KSchG § 15, KSchG § 23, KSchG § 17, BEEG § 18, KSchG § 1

**Answer:**

Die Vorschriften des Kündigungsschutzgesetzes (Erster Abschnitt) gelten nicht für Betriebe und Verwaltungen, in denen in der Regel fünf oder weniger Arbeitnehmer (ausschließlich der zu ihrer Berufsbildung Beschäftigten) beschäftigt werden; für Arbeitsverhältnisse, die nach dem 31. Dezember 2003 begonnen haben, gilt dies in Betrieben mit in der Regel zehn oder weniger Arbeitnehmern nach Maßgabe des § 23 Abs. 1 KSchG.

## T5 — in-corpus (de)

**Question:** Was regelt das Nachweisgesetz in einem Satz?

**Expectation:** Should summarize NachwG from retrieved paragraphs. refused=false.

**refused:** `true`

**Retrieved:** KSchG § 26, MiLoG § 23, BUrlG § 16, AGG § 32, AGG § 22

**Answer:**

Die geladenen Dokumente enthalten die Antwort nicht.

## F1 — out-of-corpus (de)

**Question:** Wie hoch ist das Gehalt des CEOs von Siemens?

**Expectation:** Must refuse. No invented euro amount.

**refused:** `true`

**Retrieved:** TzBfG § 6, AGG § 26g, MiLoG § 20, EntgFG § 4a, MiLoG § 8

**Answer:**

Die vorliegenden Dokumente enthalten keine Informationen über das Gehalt des CEOs von Siemens.

## F2 — out-of-corpus (de)

**Question:** Wie wird das Wetter in Karlsruhe nächste Woche?

**Expectation:** Must refuse. Weather is not in the labour-law pack.

**refused:** `true`

**Retrieved:** BUrlG § 3, MuSchG 2018 § 3, JArbSchG § 15, MuSchG 2018 § 6, ArbZG § 26

**Answer:**

Die geladenen Dokumente enthalten diese Information nicht.

## F3 — out-of-corpus (de)

**Question:** Wie viele Urlaubstage hat man gesetzlich in Frankreich?

**Expectation:** Must refuse. French law is not loaded.

**refused:** `true`

**Retrieved:** BUrlG § 3, BUrlG § 1, BUrlG § 9, MuSchG 2018 § 24, BUrlG § 4

**Answer:**

Die geladenen Dokumente enthalten keine Informationen über die gesetzlichen Urlaubstage in Frankreich.

## F4 — out-of-corpus (de)

**Question:** Welche interne Homeoffice-Regel gilt bei neoLab?

**Expectation:** Must refuse. Employer policy is not in the corpus.

**refused:** `true`

**Retrieved:** BUrlG § 3, BUrlG § 8, JArbSchG § 15, TzBfG § 12, MuSchG 2018 § 8

**Answer:**

Die geladenen Dokumente enthalten keine Informationen über eine interne Homeoffice-Regel bei neoLab.

## P1 — partially-false (de)

**Question:** Der gesetzliche Mindesturlaub beträgt 30 Tage, stimmt das?

**Expectation:** Should not agree with 30. Should correct using BUrlG (24 Werktage) or refuse if unsure.

**refused:** `false`

**Retrieved:** BUrlG § 3, BUrlG § 1, JArbSchG § 19, BUrlG § 4, BUrlG § 9

**Answer:**

Nein, das stimmt so pauschal nicht. Laut Bundesurlaubsgesetz (§ 3 Abs. 1 BUrlG) beträgt der gesetzliche Mindesturlaub jährlich mindestens 24 Werktage. Ein gesetzlicher Mindesturlaub von 30 Werktagen gilt nach § 19 Abs. 2 Nr. 1 Jugendarbeitsschutzgesetz (JArbSchG) nur für Jugendliche, die zu Beginn des Kalenderjahrs noch nicht 16 Jahre alt sind.

## P2 — partially-false (de)

**Question:** Nach dem Bundesurlaubsgesetz habe ich Anspruch auf 24 Wochen Urlaub, oder?

**Expectation:** Should reject 24 weeks; the statute speaks of Werktage, not weeks.

**refused:** `false`

**Retrieved:** BUrlG § 3, BUrlG § 1, MuSchG 2018 § 24, BUrlG § 11, JArbSchG § 19

**Answer:**

Nein, nach dem Bundesurlaubsgesetz beträgt der Urlaub jährlich mindestens 24 Werktage, nicht Wochen.

## P3 — partially-false (de)

**Question:** Das Arbeitszeitgesetz erlaubt zwölf Stunden Arbeit an jedem Werktag ohne Pause und ohne Ausnahme. Stimmt das?

**Expectation:** Should not accept this as a blanket rule. ArbZG has an 8-hour baseline and rest-break rules.

**refused:** `false`

**Retrieved:** ArbZG § 3, JArbSchG § 13, ArbZG § 4, ArbZG § 7, ArbZG § 21a

**Answer:**

Nein, das stimmt nicht. Laut Arbeitszeitgesetz (ArbZG § 3) darf die werktägliche Arbeitszeit der Arbeitnehmer acht Stunden nicht überschreiten und kann nur unter bestimmten Voraussetzungen auf bis zu zehn Stunden verlängert werden. Zudem schreibt das Gesetz in § 4 vor, dass die Arbeit bei einer Arbeitszeit von mehr als sechs bis zu neun Stunden durch Ruhepausen von mindestens 30 Minuten und bei mehr als neun Stunden von mindestens 45 Minuten zu unterbrechen ist.

## P4 — partially-false (de)

**Question:** Das Mindestlohngesetz legt den Stundenlohn fest auf genau 20 Euro. Ist das so im Gesetzestext?

**Expectation:** Should not invent 20 Euro. Either cite the actual MiLoG wording or refuse if the amount is not in the retrieved excerpts.

**refused:** `false`

**Retrieved:** MiLoG § 1, MiLoG § 20, MiLoG § 9, MiLoG § 11, MiLoG § 4

**Answer:**

Nein, das ist nicht so im Gesetzestext. Laut § 1 Absatz 2 des Mindestlohngesetzes beträgt die Höhe des Mindestlohns ab dem 1. Oktober 2022 brutto 12 Euro je Zeitstunde.

## E1 — in-corpus (en)

**Question:** How many statutory annual leave days does German federal law guarantee at minimum?

**Expectation:** Answer in English, grounded in BUrlG § 3 (24 Werktage). refused=false.

**refused:** `false`

**Retrieved:** BUrlG § 1, BUrlG § 3, JArbSchG § 19, BUrlG § 7, MuSchG 2018 § 24

**Answer:**

Der gesetzliche Erholungsurlaub beträgt nach § 3 Abs. 1 des Bundesurlaubsgesetzes (BUrlG) jährlich mindestens 24 Werktage.

## E2 — out-of-corpus (en)

**Question:** What is the salary of the Siemens CEO?

**Expectation:** Must refuse, in English.

**refused:** `true`

**Retrieved:** TzBfG § 6, MiLoG § 20, AGG § 26g, EntgFG § 4a, MiLoG § 8

**Answer:**

The loaded documents do not contain the answer.

## E3 — partially-false (en)

**Question:** German law gives every employee 30 calendar days of vacation. Is that correct?

**Expectation:** Should not confirm 30 calendar days. Point to BUrlG 24 Werktage or refuse.

**refused:** `false`

**Retrieved:** BUrlG § 1, BUrlG § 3, JArbSchG § 19, BUrlG § 7, BUrlG § 5

**Answer:**

Nein, das ist nicht korrekt. Nach dem Bundesurlaubsgesetz beträgt der Urlaub jährlich mindestens 24 Werktage.

## E4 — in-corpus (en)

**Question:** According to the Working Time Act, how long is the regular working day?

**Expectation:** Should cite ArbZG in English. refused=false if retrieval finds § 3.

**refused:** `false`

**Retrieved:** ArbZG § 3, BUrlG § 3, ArbZG § 21a, JArbSchG § 8, JArbSchG § 4

**Answer:**

Nach dem Arbeitszeitgesetz (ArbZG § 3) darf die werktägliche Arbeitszeit der Arbeitnehmer acht Stunden nicht überschreiten. Sie kann auf bis zu zehn Stunden nur verlängert werden, wenn innerhalb von sechs Kalendermonaten oder innerhalb von 24 Wochen im Durchschnitt acht Stunden werktäglich nicht überschritten werden.

## Auswertung (für die Fallstudie)

Kurzfazit nach 17 Läufen auf dem echten Index (12 Gesetze, 356 Abschnitte, `gemini-3.5-flash-lite`).

| Gruppe | Fälle | Beobachtung |
| --- | --- | --- |
| In-Korpus, Deutsch | T1–T4 | Treffer. Urlaub (24 Werktage), ArbZG (8 Stunden, Verlängerung auf 10), EntgFG (6 Wochen), KSchG § 23 mit der 5-/10-Personen-Schwelle. |
| In-Korpus, Deutsch | T5 | Fehlschlag: die Frage nach dem Nachweisgesetz holt **keinen** NachwG-Chunk. Retrieval liefert KSchG, MiLoG, BUrlG, AGG. Die Chat-Schicht verweigert korrekt — das Problem sitzt im Suchschritt, nicht im Prompt. |
| Außerhalb | F1–F4 | Alle `refused=true`, keine erfundenen Zahlen. Siemens, Wetter, Frankreich, neoLab. |
| Teilweise falsch | P1–P3 | Modell widerspricht der Falle (30 Tage, 24 Wochen, 12 Stunden ohne Pause) und korrigiert aus den Exzerpten. |
| Teilweise falsch | P4 | Sagt zu Recht „nicht 20 Euro“, zitiert aber **12 Euro ab 1. Oktober 2022** aus MiLoG § 1. Das ist treu zum geladenen Text und kann 2026 trotzdem veraltet sein. RAG wiederholt den Korpus, es prüft nicht das heutige Verordnungsblatt. |
| Englisch | E1, E3, E4 | Inhaltlich oft richtig, **Sprache oft Deutsch**, obwohl die Frage Englisch war. Der Systemprompt verlangt dieselbe Sprache wie die Frage; Flash-Lite hält sich daran nicht zuverlässig. |
| Englisch | E2 | Verweigerung auf Englisch — der einfache Out-of-corpus-Fall klappt. |

Was davon in den Website-Text gehört: (1) der Korpus ist groß genug, dass nicht alles in den Prompt passt; (2) Verweigerung funktioniert, wenn die Frage fachfremd ist; (3) der ehrliche Misserfolg ist T5 — ohne das Gesetzskürzel im Fragetext findet die Vektorsuche den NachwG nicht; (4) englische Fragen werden beantwortet, aber nicht immer auf Englisch; (5) keine Rechtsberatung, und P4 zeigt warum.

## Was passiert auf Englisch?

Die Pipeline übersetzt den Korpus nicht. Sie sucht mit dem englischen Fragesatz im **deutschen** Embedding-Raum. In dieser Serie landeten E1/E3 trotzdem bei BUrlG § 3 und E4 bei ArbZG § 3 — semantische Nähe reicht hier. Die Antwort bleibt häufig Deutsch, weil die Exzerpte Deutsch sind und das kleine Modell dem Quelltext folgt. Für die Fallstudie: Englisch als Eingabe ist möglich, eine stabile englische Ausgabe wäre ein eigener Prompt-Test (siehe unten).

## Weitere Experimente

1. **Hybrid-Suche.** T5 mit einem zweiten Stichwortindex (BM25) auf „Nachweisgesetz“ / `NachwG`, gemischt mit den Vektoren.
2. **Query-Übersetzung.** Englische Frage erst ins Deutsche drehen, dann suchen — messen, ob E1 dann englisch *und* präzise bleibt.
3. **Striktere Sprachregel.** Im JSON-Schema ein Feld `language` oder im Prompt: „If the question is English, answer in English even if excerpts are German.“
4. **Gold-Set.** 20 Fragen mit erwartetem Locator; Trefferquote@5 als Zahl in der Fallstudie, nicht nur Anekdoten.
5. **Stale law.** P4 systematisch: Mindestlohn-Betrag im XML vs. aktuelle Verordnung. Zeigt den Unterschied „im Index“ vs. „in Kraft“.
6. **Nachbar-Gesetze.** Jugendurlaub (JArbSchG) vs. Erwachsenenurlaub (BUrlG), wie in T1 — ist die Extra-Information hilfreich oder verwirrend?
7. **Top-k.** denselben Satz mit k=3 und k=8: weniger Lärm vs. mehr Chance für NachwG.
8. **Leere vs. schwache Treffer.** F2 retrieved trotzdem BUrlG § 3 (Urlaub/Wetter-Assoziation?). Schwellenwert auf die Distanz — in der Spezifikation bewusst weggelassen, lohnt ein Nachtrag.
9. **Anderes Flash-Lite vs. 3.6-flash.** Dieselbe 17er-Liste, nur das Chat-Modell tauschen; Zählung der Sprach- und Verweigerungsfehler.
10. **HTML-Entities.** P1 lieferte einmal `&#228;` statt Umlaute. Für Screenshots die Ausgabe normalisieren oder das Modell härter auf Unicode verpflichten.

Diese Datei ist das Rohprotokoll. Screenshots der HTML-Seite gehören nicht hierhin; sie kommen später auf kyryloyasko.de.

