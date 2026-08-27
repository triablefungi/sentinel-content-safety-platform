from datetime import UTC, datetime
from uuid import uuid4

from sentinel.core.normalization import normalize_text
from sentinel.core.rules import DEFAULT_RULES, RuleEngine
from sentinel.ml.protocols import ToxicityModel
from sentinel.schemas.moderation import (
    Decision,
    ModerationRequest,
    ModerationResponse,
    ModerationSignal,
)
from sentinel.threat_intelligence.service import ThreatIntelligenceService

MODEL_REVIEW_THRESHOLD = 0.40
BLOCK_THRESHOLD = 0.85


class ModerationEngine:
    """Combine deterministic rules and a swappable toxicity model."""

    def __init__(
        self,
        rule_engine: RuleEngine,
        toxicity_model: ToxicityModel | None = None,
        threat_intelligence: ThreatIntelligenceService | None = None,
    ) -> None:
        self._rule_engine = rule_engine
        self._toxicity_model = toxicity_model
        self._threat_intelligence = threat_intelligence

    @classmethod
    def default(
        cls,
        toxicity_model: ToxicityModel | None = None,
        threat_intelligence: ThreatIntelligenceService | None = None,
    ) -> "ModerationEngine":
        return cls(
            RuleEngine(DEFAULT_RULES),
            toxicity_model=toxicity_model,
            threat_intelligence=threat_intelligence,
        )

    def moderate(self, request: ModerationRequest) -> ModerationResponse:
        normalized_text = normalize_text(request.text)
        matches = self._rule_engine.evaluate(normalized_text)
        signals = [
            ModerationSignal(
                source="heuristic",
                category=match.category,
                score=match.severity,
                reason_code=match.reason_code,
            )
            for match in matches
        ]

        model_score = 0.0
        if self._toxicity_model is not None:
            model_score = self._toxicity_model.predict_score(normalized_text)
            if model_score >= MODEL_REVIEW_THRESHOLD:
                signals.append(
                    ModerationSignal(
                        source=f"ml:{self._toxicity_model.version}",
                        category="toxicity",
                        score=model_score,
                        reason_code="toxicity_probability",
                    )
                )

        threat_score = 0.0
        if self._threat_intelligence is not None:
            request_id = request.request_id or str(uuid4())
            assessment = self._threat_intelligence.assess_and_index(
                request_id=request_id,
                text=request.text,
            )
            threat_score = assessment.risk_score
            if assessment.coordinated:
                signals.append(
                    ModerationSignal(
                        source=self._threat_intelligence.source,
                        category="coordinated_abuse",
                        score=threat_score,
                        reason_code="similar_content_campaign",
                    )
                )

        rule_score = max((match.severity for match in matches), default=0.0)
        risk_score = max(rule_score, model_score, threat_score)

        if risk_score >= BLOCK_THRESHOLD:
            decision = Decision.BLOCK
        elif risk_score >= MODEL_REVIEW_THRESHOLD:
            decision = Decision.REVIEW
        else:
            decision = Decision.ALLOW

        return ModerationResponse(
            request_id=request.request_id or str(uuid4()),
            decision=decision,
            risk_score=risk_score,
            signals=signals,
            policy_version="2026-08-27",
            evaluated_at=datetime.now(UTC),
        )

    def close(self) -> None:
        if self._threat_intelligence is not None:
            self._threat_intelligence.close()
