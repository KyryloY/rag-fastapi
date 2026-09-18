from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    law: str
    paragraph: str
    locator: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    sources: list[Source]


class HealthResponse(BaseModel):
    status: str


class StatsResponse(BaseModel):
    laws: int
    chunks: int
    characters: int
    collection: str
