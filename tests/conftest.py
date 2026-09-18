from app.embeddings import EmbeddingClient
from app.parse_xml import Chunk


class KeywordEmbeddingClient:
    """Deterministic 2-D vectors for tests. No network."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        lowered = text.lower()
        if "urlaub" in lowered or "leave" in lowered:
            return [1.0, 0.0]
        return [0.0, 1.0]


def leave_chunk() -> Chunk:
    return Chunk(
        law="BUrlG",
        paragraph="3",
        locator="BUrlG § 3",
        title="Dauer des Urlaubs",
        text="Der Urlaub beträgt jährlich mindestens 24 Werktage.",
    )


def wage_chunk() -> Chunk:
    return Chunk(
        law="MiLoG",
        paragraph="1",
        locator="MiLoG § 1",
        title="",
        text="Dieses Gesetz regelt den allgemeinen Mindestlohn.",
    )
