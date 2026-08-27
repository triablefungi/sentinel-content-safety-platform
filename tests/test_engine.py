from sentinel.core.engine import ModerationEngine
from sentinel.schemas.moderation import ModerationRequest


class FakeToxicityModel:
    def __init__(self, score: float) -> None:
        self._score = score

    @property
    def version(self) -> str:
        return "fake-v1"

    def predict_score(self, text: str) -> float:
        return self._score


class RecordingToxicityModel(FakeToxicityModel):
    def __init__(self, score: float) -> None:
        super().__init__(score)
        self.received_text = ""

    def predict_score(self, text: str) -> float:
        self.received_text = text
        return super().predict_score(text)


def test_ml_score_can_route_content_to_review() -> None:
    engine = ModerationEngine.default(toxicity_model=FakeToxicityModel(0.72))

    result = engine.moderate(ModerationRequest(text="A model-only test sentence."))

    assert result.decision == "review"
    assert result.risk_score == 0.72
    assert result.signals[0].source == "ml:fake-v1"
    assert result.signals[0].category == "toxicity"
    assert result.signals[0].reason_code == "toxicity_probability"


def test_low_ml_score_keeps_safe_content_allowed() -> None:
    engine = ModerationEngine.default(toxicity_model=FakeToxicityModel(0.10))

    result = engine.moderate(ModerationRequest(text="A safe test sentence."))

    assert result.decision == "allow"
    assert result.risk_score == 0.10
    assert result.signals == []


def test_ml_model_receives_the_same_canonical_text_as_rules() -> None:
    model = RecordingToxicityModel(0.10)
    engine = ModerationEngine.default(toxicity_model=model)

    engine.moderate(ModerationRequest(text="K.1.L.L\u200b   Y.0.U"))

    assert model.received_text == "kill you"
