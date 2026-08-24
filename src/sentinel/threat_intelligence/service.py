from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from sentinel.threat_intelligence.protocols import TextEncoder, ThreatVectorStore


@dataclass(frozen=True)
class ThreatAssessment:
    match_count: int
    maximum_similarity: float
    risk_score: float

    @property
    def coordinated(self) -> bool:
        return self.match_count >= 2


class ThreatIntelligenceService:
    """Detect repeated campaigns without storing raw user text in vector payloads."""

    def __init__(
        self,
        encoder: TextEncoder,
        store: ThreatVectorStore,
        similarity_threshold: float = 0.90,
        search_limit: int = 20,
    ) -> None:
        self._encoder = encoder
        self._store = store
        self._similarity_threshold = similarity_threshold
        self._search_limit = search_limit

    @property
    def source(self) -> str:
        return f"vector:{self._encoder.version}"

    def assess_and_index(self, request_id: str, text: str) -> ThreatAssessment:
        vector = self._encoder.encode(text)
        matches = self._store.search(
            vector,
            limit=self._search_limit,
            score_threshold=self._similarity_threshold,
        )
        distinct_matches = [match for match in matches if match.request_id != request_id]
        point_id = str(uuid5(NAMESPACE_URL, f"sentinel:threat:{request_id}"))
        self._store.upsert(point_id, vector, request_id)

        match_count = len(distinct_matches)
        maximum_similarity = max(
            (match.score for match in distinct_matches),
            default=0.0,
        )
        risk_score = 0.0
        if match_count >= 5:
            risk_score = 0.90
        elif match_count >= 2:
            risk_score = min(0.84, 0.55 + (0.05 * match_count))
        return ThreatAssessment(
            match_count=match_count,
            maximum_similarity=maximum_similarity,
            risk_score=risk_score,
        )

    def close(self) -> None:
        self._store.close()
