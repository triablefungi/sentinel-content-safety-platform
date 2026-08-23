from typing import Protocol


class ToxicityModel(Protocol):
    """Boundary between the policy engine and any toxicity model implementation."""

    @property
    def version(self) -> str: ...

    def predict_score(self, text: str) -> float: ...

