from app.answer import answer_question
from app.chat import ChatResult
from app.language import LinguaDetector, resolve_question_language
from app.parse_xml import Chunk


def test_lingua_detects_english_and_german_sentences():
    detector = LinguaDetector()
    english = detector.detect(
        "How many statutory annual leave days does German federal law guarantee?"
    )
    german = detector.detect(
        "Wie viele Urlaubstage stehen gesetzlich mindestens zu?"
    )
    assert english == "en"
    assert german == "de"


def test_short_or_empty_text_falls_back_to_german():
    detector = LinguaDetector()
    assert resolve_question_language("   ", detector) == "de"


class _FixedDetector:
    def __init__(self, mapping: dict[str, str | None]) -> None:
        self.mapping = mapping

    def detect(self, text: str) -> str | None:
        for needle, code in self.mapping.items():
            if needle in text:
                return code
        return None


class _RecordingChat:
    def __init__(self, replies: list[ChatResult]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> ChatResult:
        self.calls.append((system, user))
        return self.replies.pop(0)


def _chunk() -> Chunk:
    return Chunk(
        law="BUrlG",
        paragraph="3",
        locator="BUrlG § 3",
        title="",
        text="Der Urlaub beträgt jährlich mindestens 24 Werktage.",
    )


def test_english_question_asks_for_english_answer():
    chat = _RecordingChat(
        [ChatResult(answer="The statutory minimum is 24 working days.", refused=False)]
    )
    detector = _FixedDetector({"How many": "en", "The statutory": "en"})
    result = answer_question(
        "How many leave days are guaranteed?",
        [_chunk()],
        chat,
        detector=detector,
    )
    assert result.refused is False
    assert len(chat.calls) == 1
    assert "Answer in English" in chat.calls[0][1]


def test_retries_once_when_answer_language_mismatches():
    chat = _RecordingChat(
        [
            ChatResult(answer="Der gesetzliche Mindesturlaub beträgt 24 Werktage.", refused=False),
            ChatResult(answer="The statutory minimum leave is 24 working days.", refused=False),
        ]
    )
    detector = _FixedDetector(
        {
            "How many": "en",
            "Der gesetzliche": "de",
            "The statutory": "en",
        }
    )
    result = answer_question(
        "How many leave days are guaranteed?",
        [_chunk()],
        chat,
        detector=detector,
    )
    assert len(chat.calls) == 2
    assert "Answer in English" in chat.calls[1][1]
    assert "previous answer was not in English" in chat.calls[1][1]
    assert result.answer.startswith("The statutory")


def test_german_question_does_not_retry_matching_german_answer():
    chat = _RecordingChat(
        [ChatResult(answer="Der gesetzliche Mindesturlaub beträgt 24 Werktage.", refused=False)]
    )
    detector = _FixedDetector(
        {
            "Wie viele": "de",
            "Der gesetzliche": "de",
        }
    )
    answer_question("Wie viele Urlaubstage stehen zu?", [_chunk()], chat, detector=detector)
    assert len(chat.calls) == 1
    assert "Antworte auf Deutsch" in chat.calls[0][1]
