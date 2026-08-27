import json
import warnings
from io import BytesIO
from pathlib import Path
from typing import Any

from sentinel.multimodal.errors import ImageTooLargeError, InvalidImageError
from sentinel.multimodal.image import MAX_IMAGE_PIXELS, ValidatedImage
from sentinel.schemas.moderation import SafetyCategory


class TransformerImageSafetyModel:
    """Local Hugging Face image-classification adapter with reviewed label mapping."""

    def __init__(
        self,
        model: Any,
        processor: Any,
        device: Any,
        version: str,
        label_categories: dict[int, SafetyCategory],
    ) -> None:
        self._model = model
        self._processor = processor
        self._device = device
        self._version = version
        self._label_categories = label_categories

    @property
    def version(self) -> str:
        return self._version

    @classmethod
    def load(cls, path: Path) -> "TransformerImageSafetyModel":
        metadata_path = path / "sentinel_image_metadata.json"
        if not metadata_path.exists():
            raise ValueError(f"reviewed image-model metadata is missing: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        raw_mapping = metadata.get("label_categories")
        if not isinstance(raw_mapping, dict) or not raw_mapping:
            raise ValueError("image-model metadata requires a non-empty label_categories mapping")

        import torch
        from transformers import AutoImageProcessor, AutoModelForImageClassification

        processor = AutoImageProcessor.from_pretrained(path)
        model = AutoModelForImageClassification.from_pretrained(path)
        label_categories: dict[int, SafetyCategory] = {}
        for model_label, category in raw_mapping.items():
            matching_ids = [
                int(index)
                for index, label in model.config.id2label.items()
                if label == model_label
            ]
            if not matching_ids:
                raise ValueError(f"mapped model label does not exist: {model_label}")
            safety_category = SafetyCategory(category)
            if safety_category not in {
                SafetyCategory.SEXUAL_CONTENT,
                SafetyCategory.GRAPHIC_VIOLENCE,
            }:
                raise ValueError(f"unsupported image category mapping: {category}")
            label_categories[matching_ids[0]] = safety_category

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        return cls(
            model=model,
            processor=processor,
            device=device,
            version=str(metadata["model_version"]),
            label_categories=label_categories,
        )

    def predict_scores(self, image: ValidatedImage) -> dict[SafetyCategory, float]:
        import torch
        from PIL import Image, ImageOps, UnidentifiedImageError

        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(image.data)) as candidate:
                    sanitized = ImageOps.exif_transpose(candidate).convert("RGB")
                    sanitized.load()
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise ImageTooLargeError("image exceeds the safe decoded-pixel limit") from error
        except (UnidentifiedImageError, OSError, SyntaxError) as error:
            raise InvalidImageError("image could not be decoded safely") from error

        encoded = self._processor(images=sanitized, return_tensors="pt")
        encoded = {name: tensor.to(self._device) for name, tensor in encoded.items()}
        with torch.inference_mode():
            probabilities = torch.softmax(self._model(**encoded).logits, dim=-1)[0]
        scores: dict[SafetyCategory, float] = {}
        for index, category in self._label_categories.items():
            scores[category] = max(
                scores.get(category, 0.0),
                float(probabilities[index].cpu().item()),
            )
        return scores
