from dataclasses import dataclass
import json
from typing import Protocol

from google import genai
from google.genai import types

from app.config import Settings


@dataclass(frozen=True)
class ChatResult:
    answer: str
    refused: bool


class ChatClient(Protocol):
    def complete(self, system: str, user: str) -> ChatResult: ...


ANSWER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "refused": {"type": "boolean"},
    },
    "required": ["answer", "refused"],
}


class GeminiChatClient:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.gemini_chat_model
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def complete(self, system: str, user: str) -> ChatResult:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=ANSWER_JSON_SCHEMA,
                ),
            )
            payload = json.loads(response.text)
            return ChatResult(
                answer=str(payload["answer"]),
                refused=bool(payload["refused"]),
            )
        except Exception as exc:
            raise RuntimeError("The language model is currently unavailable") from exc
