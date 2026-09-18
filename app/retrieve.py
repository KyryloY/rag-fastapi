from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import Documents, Embeddings

from app.embeddings import EmbeddingClient
from app.parse_xml import Chunk

COLLECTION_NAME = "labour_law"


@dataclass(frozen=True)
class IndexStats:
    laws: int
    chunks: int
    characters: int
    collection: str


class _ClientEmbeddingFunction:
    """Chroma embedding function that shares query geometry for add and search."""

    def __init__(self, embedding_client: EmbeddingClient) -> None:
        self._embedding_client = embedding_client

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embedding_client.embed_query(text) for text in input]

    def name(self) -> str:
        return "injectable_client"

    def is_legacy(self) -> bool:
        return True

    def get_config(self) -> dict[str, Any]:
        return {}


class _BoundCollection:
    def __init__(self, client: chromadb.ClientAPI, collection: Any) -> None:
        self.client = client
        self.collection = collection

    def count(self) -> int:
        return self.collection.count()

    def get(self, **kwargs: Any) -> Any:
        return self.collection.get(**kwargs)

    def query(self, **kwargs: Any) -> Any:
        return self.collection.query(**kwargs)

    def add(self, **kwargs: Any) -> Any:
        return self.collection.add(**kwargs)


def _embedding_function(embedding_client: EmbeddingClient) -> _ClientEmbeddingFunction:
    return _ClientEmbeddingFunction(embedding_client)


def open_collection(path: Path, embedding_client: EmbeddingClient) -> _BoundCollection:
    client = chromadb.PersistentClient(path=str(path))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=_embedding_function(embedding_client),
    )
    return _BoundCollection(client, collection)


def replace_chunks(
    collection: _BoundCollection,
    chunks: list[Chunk],
    embedding_client: EmbeddingClient,
) -> None:
    client = collection.client
    embedding_fn = _embedding_function(embedding_client)
    client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )
    client.delete_collection(COLLECTION_NAME)
    new_collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=embedding_fn,
    )
    collection.collection = new_collection
    if not chunks:
        return
    ids = [f"{chunk.law}-{chunk.paragraph}-{i}" for i, chunk in enumerate(chunks)]
    metadatas = [
        {
            "law": chunk.law,
            "paragraph": chunk.paragraph,
            "locator": chunk.locator,
            "title": chunk.title,
        }
        for chunk in chunks
    ]
    documents = [chunk.text for chunk in chunks]
    embeddings = embedding_client.embed_documents(documents)
    new_collection.add(
        ids=ids,
        metadatas=metadatas,
        documents=documents,
        embeddings=embeddings,
    )


def query_chunks(
    collection: _BoundCollection,
    question: str,
    embedding_client: EmbeddingClient,
    k: int = 5,
) -> list[Chunk]:
    count = collection.count()
    if count == 0:
        return []
    n_results = min(k, count)
    result = collection.query(
        query_embeddings=[embedding_client.embed_query(question)],
        n_results=n_results,
        include=["metadatas", "documents"],
    )
    metadatas = (result.get("metadatas") or [[]])[0] or []
    documents = (result.get("documents") or [[]])[0] or []
    hits: list[Chunk] = []
    for meta, document in zip(metadatas, documents):
        meta = meta or {}
        hits.append(
            Chunk(
                law=str(meta.get("law", "")),
                paragraph=str(meta.get("paragraph", "")),
                locator=str(meta.get("locator", "")),
                title=str(meta.get("title", "")),
                text=document or "",
            )
        )
    return hits


def collection_stats(collection: _BoundCollection) -> IndexStats:
    try:
        count = collection.count()
    except Exception:
        return IndexStats(0, 0, 0, COLLECTION_NAME)
    if count == 0:
        return IndexStats(0, 0, 0, COLLECTION_NAME)
    data = collection.get(include=["metadatas", "documents"])
    metadatas = data.get("metadatas") or []
    documents = data.get("documents") or []
    laws = {str(meta["law"]) for meta in metadatas if meta and "law" in meta}
    characters = sum(len(document) for document in documents if document)
    return IndexStats(
        laws=len(laws),
        chunks=count,
        characters=characters,
        collection=COLLECTION_NAME,
    )
