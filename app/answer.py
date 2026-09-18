from app.chat import ChatClient, ChatResult
from app.language import (
    DEFAULT_LANGUAGE,
    LanguageDetector,
    LinguaDetector,
    resolve_question_language,
)
from app.parse_xml import Chunk

SYSTEM_PROMPT = """You answer questions using only the statute excerpts in the user message.
If the excerpts are insufficient, say that the loaded documents do not contain the answer.
Do not invent figures, company facts, or legal results.
Do not invent citations.
Return JSON only with keys "answer" (string) and "refused" (boolean).
Set refused to true only when the excerpts do not contain the answer.
"""

_LANGUAGE_INSTRUCTION = {
    "en": "Answer in English. Do not answer in German.",
    "de": "Antworte auf Deutsch.",
}

_RETRY_INSTRUCTION = {
    "en": "Your previous answer was not in English. Answer in English only.",
    "de": "Deine vorherige Antwort war nicht auf Deutsch. Antworte nur auf Deutsch.",
}

_default_detector: LanguageDetector | None = None


def default_language_detector() -> LanguageDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = LinguaDetector()
    return _default_detector


def build_user_prompt(
    question: str,
    chunks: list[Chunk],
    *,
    language: str = DEFAULT_LANGUAGE,
    retry: bool = False,
) -> str:
    parts = [
        _LANGUAGE_INSTRUCTION[language],
    ]
    if retry:
        parts.append(_RETRY_INSTRUCTION[language])
    parts.extend(["", f"Question: {question}", "", "Excerpts:"])
    for chunk in chunks:
        parts.append(f"Locator: {chunk.locator}")
        if chunk.title:
            parts.append(f"Title: {chunk.title}")
        parts.append(f"Text: {chunk.text}")
        parts.append("")
    return "\n".join(parts).strip()


def answer_question(
    question: str,
    chunks: list[Chunk],
    chat_client: ChatClient,
    detector: LanguageDetector | None = None,
) -> ChatResult:
    detector = detector or default_language_detector()
    language = resolve_question_language(question, detector)
    result = chat_client.complete(
        SYSTEM_PROMPT,
        build_user_prompt(question, chunks, language=language),
    )
    answer_language = detector.detect(result.answer)
    if answer_language in {None, language}:
        return result
    return chat_client.complete(
        SYSTEM_PROMPT,
        build_user_prompt(question, chunks, language=language, retry=True),
    )
