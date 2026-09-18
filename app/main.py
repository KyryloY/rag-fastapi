from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.answer import answer_question
from app.chat import ChatClient, GeminiChatClient
from app.config import Settings
from app.embeddings import EmbeddingClient, GeminiEmbeddingClient
from app.retrieve import (
    COLLECTION_NAME,
    IndexStats,
    collection_stats,
    open_collection,
    query_chunks,
)
from app.schemas import AskRequest, AskResponse, HealthResponse, Source, StatsResponse

_EMPTY_INDEX_DETAIL = "The document index is empty. Run ingest first."
_MODEL_UNAVAILABLE_DETAIL = "The language model is currently unavailable"
_MAX_QUESTION_LENGTH = 2000
_SNIPPET_LENGTH = 240
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _zero_stats() -> IndexStats:
    return IndexStats(0, 0, 0, COLLECTION_NAME)


def create_app(
    embedding_client: EmbeddingClient,
    chat_client: ChatClient,
    chroma_path: Path,
) -> FastAPI:
    app = FastAPI()

    def _load_stats() -> IndexStats:
        try:
            collection = open_collection(chroma_path, embedding_client)
        except Exception:
            return _zero_stats()
        return collection_stats(collection)

    @app.get("/")
    def home(request: Request):
        return templates.TemplateResponse(request, "index.html")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/stats", response_model=StatsResponse)
    def stats() -> StatsResponse:
        index = _load_stats()
        return StatsResponse(
            laws=index.laws,
            chunks=index.chunks,
            characters=index.characters,
            collection=index.collection,
        )

    @app.post("/ask", response_model=AskResponse)
    def ask(body: AskRequest) -> AskResponse:
        question = body.question.strip()
        if not question or len(question) > _MAX_QUESTION_LENGTH:
            raise HTTPException(status_code=400, detail="Invalid question")
        try:
            collection = open_collection(chroma_path, embedding_client)
        except Exception:
            raise HTTPException(status_code=503, detail=_EMPTY_INDEX_DETAIL)
        if collection.count() == 0:
            raise HTTPException(status_code=503, detail=_EMPTY_INDEX_DETAIL)
        chunks = query_chunks(collection, question, embedding_client)
        sources = [
            Source(
                law=chunk.law,
                paragraph=chunk.paragraph,
                locator=chunk.locator,
                snippet=chunk.text[:_SNIPPET_LENGTH],
            )
            for chunk in chunks
        ]
        try:
            result = answer_question(question, chunks, chat_client)
        except Exception:
            raise HTTPException(status_code=503, detail=_MODEL_UNAVAILABLE_DETAIL)
        return AskResponse(answer=result.answer, refused=result.refused, sources=sources)

    return app


def create_default_app() -> FastAPI:
    settings = Settings()
    return create_app(
        GeminiEmbeddingClient(settings),
        GeminiChatClient(settings),
        settings.chroma_path,
    )

