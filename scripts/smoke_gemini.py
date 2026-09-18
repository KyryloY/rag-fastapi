"""Smoke-test Gemini key and model IDs. Never print the API key."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent / ".env")
key = os.environ.get("GEMINI_API_KEY", "")
print("key_present:", bool(key and len(key) > 20))
print("key_prefix:", (key[:6] + "...") if key else "missing")

client = genai.Client(api_key=key)

chat_candidates = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-flash-latest",
]
embed_candidates = [
    "gemini-embedding-001",
    "gemini-embedding-2",
    "text-embedding-004",
]


def try_chat(model: str) -> str:
    try:
        response = client.models.generate_content(
            model=model,
            contents='Return JSON {"ok": true} and nothing else.',
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = (response.text or "").replace("\n", " ")[:120]
        return f"OK {text}"
    except Exception as exc:
        msg = str(exc).split("\n")[0][:240]
        return f"FAIL {type(exc).__name__}: {msg}"


def try_embed(model: str) -> str:
    try:
        response = client.models.embed_content(model=model, contents="Urlaubstage")
        embeddings = getattr(response, "embeddings", None) or []
        values = getattr(embeddings[0], "values", None) if embeddings else None
        n = len(values) if values is not None else 0
        return f"OK dim={n}"
    except Exception as exc:
        msg = str(exc).split("\n")[0][:240]
        return f"FAIL {type(exc).__name__}: {msg}"


print("\n== chat ==")
for model in chat_candidates:
    print(f"{model}: {try_chat(model)}")

print("\n== embeddings ==")
for model in embed_candidates:
    print(f"{model}: {try_embed(model)}")
