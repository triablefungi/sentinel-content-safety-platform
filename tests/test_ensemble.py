import pytest

from sentinel.ml.ensemble import MaxScoreToxicityEnsemble


class FixedModel:
    def __init__(self, version: str, score: float) -> None:
        self._version = version
        self._score = score

    @property
    def version(self) -> str:
        return self._version

    def predict_score(self, text: str) -> float:
        return self._score


def test_max_score_ensemble_uses_strictest_member() -> None:
    ensemble = MaxScoreToxicityEnsemble(
        [FixedModel("model-a", 0.35), FixedModel("model-b", 0.82)]
    )

    assert ensemble.version == "sentinel-max-ensemble-v1"
    assert ensemble.member_versions == ("model-a", "model-b")
    assert ensemble.predict_score("example") == pytest.approx(0.82)


def test_max_score_ensemble_requires_multiple_members() -> None:
    with pytest.raises(ValueError, match="at least two"):
        MaxScoreToxicityEnsemble([FixedModel("only", 0.5)])
