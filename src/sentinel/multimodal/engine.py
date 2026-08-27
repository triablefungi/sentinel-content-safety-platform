from datetime import UTC, datetime
from uuid import uuid4

from sentinel.core.engine import BLOCK_THRESHOLD, MODEL_REVIEW_THRESHOLD, ModerationEngine
from sentinel.multimodal.image import decode_image
from sentinel.multimodal.protocols import ImageSafetyModel
from sentinel.schemas.moderation import (
    Decision,
    ImageMetadata,
    ModerationRequest,
    ModerationSignal,
    MultimodalModerationRequest,
    MultimodalModerationResponse,
    SafetyCategory,
)


class MultimodalModerationEngine:
    """Fuse text and image safety evidence under one auditable policy."""

    def __init__(
        self,
        text_engine: ModerationEngine,
        image_model: ImageSafetyModel,
    ) -> None:
        self._text_engine = text_engine
        self._image_model = image_model

    def moderate(self, request: MultimodalModerationRequest) -> MultimodalModerationResponse:
        request_id = request.request_id or str(uuid4())
        decoded = decode_image(request.image_base64, request.media_type)
        image_scores = self._image_model.predict_scores(decoded)
        for category, score in image_scores.items():
            if category not in {
                SafetyCategory.SEXUAL_CONTENT,
                SafetyCategory.GRAPHIC_VIOLENCE,
            }:
                raise ValueError(f"unsupported image safety category: {category}")
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"image score must be within [0, 1], got {score}")

        signals = [
            ModerationSignal(
                source=f"vision:{self._image_model.version}",
                category=category,
                score=score,
                reason_code="image_probability",
            )
            for category, score in sorted(image_scores.items(), key=lambda item: item[0].value)
            if score >= MODEL_REVIEW_THRESHOLD
        ]
        image_risk = max(image_scores.values(), default=0.0)
        text_risk = 0.0
        modalities = ["image"]
        if request.text is not None:
            text_result = self._text_engine.moderate(
                ModerationRequest(text=request.text, request_id=request_id)
            )
            text_risk = text_result.risk_score
            signals = [*text_result.signals, *signals]
            modalities.insert(0, "text")
            text_intervenes = text_risk >= MODEL_REVIEW_THRESHOLD
            image_intervenes = image_risk >= MODEL_REVIEW_THRESHOLD
            if text_intervenes != image_intervenes:
                signals.append(
                    ModerationSignal(
                        source="policy:multimodal-fusion-v1",
                        category=SafetyCategory.CROSS_MODAL_DISAGREEMENT,
                        score=max(text_risk, image_risk),
                        reason_code="modality_disagreement",
                    )
                )

        risk_score = max(text_risk, image_risk)
        if risk_score >= BLOCK_THRESHOLD:
            decision = Decision.BLOCK
        elif risk_score >= MODEL_REVIEW_THRESHOLD:
            decision = Decision.REVIEW
        else:
            decision = Decision.ALLOW

        return MultimodalModerationResponse(
            request_id=request_id,
            decision=decision,
            risk_score=risk_score,
            signals=signals,
            policy_version="2026-08-27-multimodal-v1",
            evaluated_at=datetime.now(UTC),
            modalities=modalities,
            image=ImageMetadata(
                format=decoded.format,
                width=decoded.width,
                height=decoded.height,
                bytes_received=decoded.bytes_received,
            ),
        )
