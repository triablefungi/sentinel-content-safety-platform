import pytest

from sentinel.core.engine import ModerationEngine
from sentinel.multimodal.engine import MultimodalModerationEngine
from sentinel.schemas.moderation import (
    ImageMediaType,
    MultimodalModerationRequest,
    SafetyCategory,
)


class FixedImageModel:
    def __init__(self, scores: dict[SafetyCategory, float]) -> None:
        self._scores = scores

    @property
    def version(self) -> str:
        return "fixed-image-v1"

    def predict_scores(self, image):  # type: ignore[no-untyped-def]
        return self._scores


def image_payload() -> str:
    return (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42Y"
        "AAAAASUVORK5CYII="
    )


def request(text: str | None = None) -> MultimodalModerationRequest:
    return MultimodalModerationRequest(
        image_base64=image_payload(),
        media_type=ImageMediaType.PNG,
        text=text,
        request_id="multimodal-test",
    )


def test_safe_text_and_image_are_allowed() -> None:
    engine = MultimodalModerationEngine(
        ModerationEngine.default(),
        FixedImageModel({SafetyCategory.SEXUAL_CONTENT: 0.05}),
    )

    result = engine.moderate(request("Thank you for the explanation."))

    assert result.decision == "allow"
    assert result.risk_score == pytest.approx(0.05)
    assert result.modalities == ["text", "image"]
    assert result.signals == []


def test_high_image_risk_blocks_image_only_request() -> None:
    engine = MultimodalModerationEngine(
        ModerationEngine.default(),
        FixedImageModel({SafetyCategory.GRAPHIC_VIOLENCE: 0.92}),
    )

    result = engine.moderate(request())

    assert result.decision == "block"
    assert result.risk_score == pytest.approx(0.92)
    assert result.signals[0].source == "vision:fixed-image-v1"
    assert result.signals[0].category == "graphic_violence"


def test_cross_modal_disagreement_is_exposed_without_weakening_block() -> None:
    engine = MultimodalModerationEngine(
        ModerationEngine.default(),
        FixedImageModel({SafetyCategory.SEXUAL_CONTENT: 0.05}),
    )

    result = engine.moderate(request("I will kill you."))

    assert result.decision == "block"
    assert result.risk_score == pytest.approx(0.95)
    assert result.signals[-1].category == "cross_modal_disagreement"
    assert result.signals[-1].reason_code == "modality_disagreement"


def test_invalid_image_model_score_fails_closed() -> None:
    engine = MultimodalModerationEngine(
        ModerationEngine.default(),
        FixedImageModel({SafetyCategory.SEXUAL_CONTENT: 1.2}),
    )

    with pytest.raises(ValueError, match="within"):
        engine.moderate(request())
