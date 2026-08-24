from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SimilarContentMatch:
    request_id: str
    score: float


class TextEncoder(Protocol):
    @property
    def dimension(self) -> int: ...

    @property
    def version(self) -> str: ...

    def encode(self, text: str) -> list[float]: ...


class ThreatVectorStore(Protocol):
    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[SimilarContentMatch]: ...

    def upsert(self, point_id: str, vector: list[float], request_id: str) -> None: ...

    def close(self) -> None: ...
