from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatResult:
    answer: str
    refused: bool


class ChatClient(Protocol):
    def complete(self, system: str, user: str) -> ChatResult: ...
