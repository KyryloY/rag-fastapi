"""Live check of GeminiChatClient JSON answers. Does not print the API key."""
from app.answer import SYSTEM_PROMPT
from app.chat import GeminiChatClient
from app.config import Settings
from app.embeddings import GeminiEmbeddingClient

settings = Settings()
print("chat_model:", settings.gemini_chat_model)
print("embed_model:", settings.gemini_embedding_model)
print("key_loaded:", bool(settings.gemini_api_key))

chat = GeminiChatClient(settings)
result = chat.complete(
    SYSTEM_PROMPT,
    "Question: Wie viele Urlaubstage?\n\n"
    "Excerpt 1\nLocator: BUrlG § 3\nText: Der Urlaub beträgt jährlich mindestens 24 Werktage.",
)
print("leave_refused:", result.refused)
print("leave_has_24:", "24" in result.answer)
print("leave_answer_preview:", result.answer[:180].encode("utf-8", "replace").decode("utf-8"))

refused = chat.complete(
    SYSTEM_PROMPT,
    "Question: Wie hoch ist das Gehalt des CEOs von Siemens?\n\n"
    "Excerpt 1\nLocator: BUrlG § 3\nText: Der Urlaub beträgt jährlich mindestens 24 Werktage.",
)
print("ceo_refused:", refused.refused)
print("ceo_answer_preview:", refused.answer[:180].replace("\n", " "))

embed = GeminiEmbeddingClient(settings)
vector = embed.embed_query("Urlaubstage")
print("embed_dim:", len(vector))
