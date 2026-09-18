from typing import Protocol

from lingua import Language, LanguageDetectorBuilder

SUPPORTED_LANGUAGES = frozenset({"de", "en"})
DEFAULT_LANGUAGE = "de"

_LANGUAGE_NAMES = {
    "de": "German",
    "en": "English",
}


class LanguageDetector(Protocol):
    def detect(self, text: str) -> str | None:
        """Return 'de', 'en', or None if the language is unclear."""


class LinguaDetector:
    def __init__(self) -> None:
        self._detector = LanguageDetectorBuilder.from_languages(
            Language.ENGLISH,
            Language.GERMAN,
        ).build()

    def detect(self, text: str) -> str | None:
        if not text.strip():
            return None
        language = self._detector.detect_language_of(text)
        if language is None:
            return None
        code = language.iso_code_639_1.name.lower()
        if code in SUPPORTED_LANGUAGES:
            return code
        return None


def language_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code, _LANGUAGE_NAMES[DEFAULT_LANGUAGE])


def resolve_question_language(text: str, detector: LanguageDetector) -> str:
    detected = detector.detect(text)
    if detected in SUPPORTED_LANGUAGES:
        return detected
    return DEFAULT_LANGUAGE
