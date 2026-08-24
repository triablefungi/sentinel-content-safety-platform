import math
from typing import Any

from sentinel.threat_intelligence.protocols import SimilarContentMatch


class QdrantThreatVectorStore:
    """Qdrant adapter that stores vectors and non-content identifiers only."""

    def __init__(self, client: Any, collection_name: str) -> None:
        self._client = client
        self._collection_name = collection_name

    @classmethod
    def connect(
        cls,
        url: str,
        collection_name: str,
        vector_size: int,
    ) -> "QdrantThreatVectorStore":
        from qdrant_client import QdrantClient, models

        client = QdrantClient(url=url)
        if not client.collection_exists(collection_name=collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
        return cls(client, collection_name)

    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[SimilarContentMatch]:
        result = self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )
        return [
            SimilarContentMatch(
                request_id=str(point.payload["request_id"]),
                score=float(point.score or 0.0),
            )
            for point in result.points
            if point.payload and "request_id" in point.payload
        ]

    def upsert(self, point_id: str, vector: list[float], request_id: str) -> None:
        from qdrant_client import models

        self._client.upsert(
            collection_name=self._collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={"request_id": request_id},
                )
            ],
            wait=True,
        )

    def close(self) -> None:
        self._client.close()


class InMemoryThreatVectorStore:
    """Cosine-search adapter for deterministic tests."""

    def __init__(self) -> None:
        self.points: dict[str, tuple[list[float], str]] = {}

    def search(
        self,
        vector: list[float],
        limit: int,
        score_threshold: float,
    ) -> list[SimilarContentMatch]:
        matches = []
        for stored_vector, request_id in self.points.values():
            score = self._cosine(vector, stored_vector)
            if score >= score_threshold:
                matches.append(SimilarContentMatch(request_id=request_id, score=score))
        return sorted(matches, key=lambda match: match.score, reverse=True)[:limit]

    def upsert(self, point_id: str, vector: list[float], request_id: str) -> None:
        self.points[point_id] = (vector, request_id)

    def close(self) -> None:
        return None

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)
