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


class ModerationEngine:
    """Combine deterministic rules and a swappable toxicity model."""

    def __init__(
        self,
        rule_engine: RuleEngine,
        toxicity_model: ToxicityModel | None = None,
    ) -> None:
        self._rule_engine = rule_engine
        self._toxicity_model = toxicity_model

    @classmethod
    def default(cls, toxicity_model: ToxicityModel | None = None) -> "ModerationEngine":
        return cls(RuleEngine(DEFAULT_RULES), toxicity_model=toxicity_model)

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
            model_score = self._toxicity_model.predict_score(request.text)
            if model_score >= 0.50:
                signals.append(
                    ModerationSignal(
                        source=f"ml:{self._toxicity_model.version}",
                        category="toxicity",
                        score=model_score,
                        reason_code="toxicity_probability",
                    )
                )

        rule_score = max((match.severity for match in matches), default=0.0)
        risk_score = max(rule_score, model_score)

        if risk_score >= 0.85:
            decision = Decision.BLOCK
        elif risk_score >= 0.50:
            decision = Decision.REVIEW
        else:
            decision = Decision.ALLOW

        return ModerationResponse(
            request_id=request.request_id or str(uuid4()),
            decision=decision,
            risk_score=risk_score,
            signals=signals,
            policy_version="2026-08-01",
            evaluated_at=datetime.now(UTC),
        )
