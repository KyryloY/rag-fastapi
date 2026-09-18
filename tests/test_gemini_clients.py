from types import SimpleNamespace

import pytest

from app.chat import GeminiChatClient
from app.config import Settings
from app.embeddings import GeminiEmbeddingClient
from google.genai.errors import APIError


class _FakeModels:
    def __init__(self, embed_impl=None, generate_impl=None):
        self.embed_impl = embed_impl
        self.generate_impl = generate_impl
        self.embed_calls: list[dict] = []
        self.generate_calls: list[dict] = []

    def embed_content(self, **kwargs):
        self.embed_calls.append(kwargs)
        return self.embed_impl(**kwargs)

    def generate_content(self, **kwargs):
        self.generate_calls.append(kwargs)
        return self.generate_impl(**kwargs)


class _FakeGenaiClient:
    def __init__(self, models: _FakeModels):
        self.models = models


def _settings() -> Settings:
    return Settings(
        gemini_api_key="test-key",
        gemini_embedding_model="gemini-embedding-001",
        gemini_chat_model="gemini-2.0-flash",
    )


def test_embed_query_returns_values(monkeypatch):
    models = _FakeModels(
        embed_impl=lambda **kwargs: SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1, 0.2])]
        )
    )
    monkeypatch.setattr(
        "app.embeddings.genai.Client",
        lambda api_key: _FakeGenaiClient(models),
    )
    client = GeminiEmbeddingClient(_settings())
    assert client.embed_query("hello") == [0.1, 0.2]
    assert models.embed_calls[0]["model"] == "gemini-embedding-001"
    assert models.embed_calls[0]["contents"] == "hello"


def test_embed_documents_sleeps_and_retries_429(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr("app.embeddings.time.sleep", sleeps.append)

    attempts = {"n": 0}

    def embed_impl(**kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise APIError(429, {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"})
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 0.0])])

    models = _FakeModels(embed_impl=embed_impl)
    monkeypatch.setattr(
        "app.embeddings.genai.Client",
        lambda api_key: _FakeGenaiClient(models),
    )
    client = GeminiEmbeddingClient(_settings())
    vectors = client.embed_documents(["a", "b"])
    assert vectors == [[1.0, 0.0], [1.0, 0.0]]
    assert 5.0 in sleeps
    assert 0.4 in sleeps


def test_chat_complete_parses_json(monkeypatch):
    def generate_impl(**kwargs):
        return SimpleNamespace(text='{"answer": "24 Werktage", "refused": false}')

    models = _FakeModels(generate_impl=generate_impl)
    monkeypatch.setattr(
        "app.chat.genai.Client",
        lambda api_key: _FakeGenaiClient(models),
    )
    client = GeminiChatClient(_settings())
    result = client.complete("sys", "user question")
    assert result.answer == "24 Werktage"
    assert result.refused is False
    call = models.generate_calls[0]
    assert call["model"] == "gemini-2.0-flash"
    assert call["contents"] == "user question"
    config = call["config"]
    mime = getattr(config, "response_mime_type", None) or config.get("response_mime_type")
    assert mime == "application/json"


def test_chat_complete_wraps_api_errors(monkeypatch):
    def generate_impl(**kwargs):
        raise APIError(503, {"message": "down", "status": "UNAVAILABLE"})

    models = _FakeModels(generate_impl=generate_impl)
    monkeypatch.setattr(
        "app.chat.genai.Client",
        lambda api_key: _FakeGenaiClient(models),
    )
    client = GeminiChatClient(_settings())
    with pytest.raises(RuntimeError):
        client.complete("sys", "user question")
