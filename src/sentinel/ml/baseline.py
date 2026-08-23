from pathlib import Path
from typing import Any


class SklearnToxicityModel:
    """Inference adapter for the serialized scikit-learn baseline."""

    def __init__(self, pipeline: Any, version: str) -> None:
        self._pipeline = pipeline
        self._version = version

    @property
    def version(self) -> str:
        return self._version

    @classmethod
    def load(cls, path: Path) -> "SklearnToxicityModel":
        import joblib

        bundle = joblib.load(path)
        return cls(
            pipeline=bundle["pipeline"],
            version=bundle["metadata"]["model_version"],
        )

    def predict_score(self, text: str) -> float:
        probability = self._pipeline.predict_proba([text])[0][1]
        return float(probability)

