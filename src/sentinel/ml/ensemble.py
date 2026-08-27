from collections.abc import Sequence

from sentinel.ml.protocols import ToxicityModel

ENSEMBLE_VERSION = "sentinel-max-ensemble-v1"


class MaxScoreToxicityEnsemble:
    """Recall-oriented ensemble in which the strictest model score wins."""

    def __init__(self, models: Sequence[ToxicityModel]) -> None:
        if len(models) < 2:
            raise ValueError("max-score ensemble requires at least two models")
        self._models = tuple(models)

    @property
    def version(self) -> str:
        return ENSEMBLE_VERSION

    @property
    def member_versions(self) -> tuple[str, ...]:
        return tuple(model.version for model in self._models)

    def predict_score(self, text: str) -> float:
        return max(model.predict_score(text) for model in self._models)
