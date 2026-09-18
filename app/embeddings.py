import time
from typing import Protocol

from google import genai
from google.genai.errors import APIError

from app.config import Settings

_EMBED_PAUSE_SECONDS = 0.4
_RATE_LIMIT_BACKOFF_SECONDS = 5
_RATE_LIMIT_RETRIES = 5


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class GeminiEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._model = settings.gemini_embedding_model
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for index, text in enumerate(texts):
            vectors.append(self.embed_query(text))
            if index < len(texts) - 1:
                time.sleep(_EMBED_PAUSE_SECONDS)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        last_error: Exception | None = None
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            try:
                response = self._client.models.embed_content(
                    model=self._model,
                    contents=text,
                )
                return list(response.embeddings[0].values)
            except APIError as exc:
                last_error = exc
                if exc.code != 429 or attempt >= _RATE_LIMIT_RETRIES:
                    raise
                time.sleep(_RATE_LIMIT_BACKOFF_SECONDS)
        raise last_error  # pragma: no cover
