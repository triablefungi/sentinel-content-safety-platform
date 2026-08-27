from typing import Protocol

from sentinel.multimodal.image import ValidatedImage
from sentinel.schemas.moderation import SafetyCategory


class ImageSafetyModel(Protocol):
    """Boundary between multimodal policy and a local vision model."""

    @property
    def version(self) -> str: ...

    def predict_scores(self, image: ValidatedImage) -> dict[SafetyCategory, float]: ...
