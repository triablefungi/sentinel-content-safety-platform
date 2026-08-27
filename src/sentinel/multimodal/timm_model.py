import hashlib
import json
import warnings
from io import BytesIO
from pathlib import Path
from typing import Any

from sentinel.multimodal.errors import ImageTooLargeError, InvalidImageError
from sentinel.multimodal.image import MAX_IMAGE_PIXELS, ValidatedImage
from sentinel.schemas.moderation import SafetyCategory

_SUPPORTED_CATEGORIES = {
    SafetyCategory.SEXUAL_CONTENT,
    SafetyCategory.GRAPHIC_VIOLENCE,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_metadata(path: Path) -> dict[str, Any]:
    metadata_path = path / "sentinel_image_metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"reviewed image-model metadata is missing: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    required = {
        "model_version",
        "backend",
        "architecture",
        "weights_file",
        "weights_sha256",
        "label_names",
        "label_categories",
        "input_size",
        "mean",
        "std",
    }
    missing = sorted(required.difference(metadata))
    if missing:
        raise ValueError(f"image-model metadata is missing fields: {', '.join(missing)}")
    if metadata["backend"] != "timm-safetensors":
        raise ValueError(f"unsupported image-model backend: {metadata['backend']}")
    return metadata


class TimmImageSafetyModel:
    """Offline timm adapter whose weights and label semantics are reviewed at load time."""

    def __init__(
        self,
        model: Any,
        transform: Any,
        device: Any,
        version: str,
        label_categories: dict[int, SafetyCategory],
    ) -> None:
        self._model = model
        self._transform = transform
        self._device = device
        self._version = version
        self._label_categories = label_categories

    @property
    def version(self) -> str:
        return self._version

    @classmethod
    def load(cls, path: Path) -> "TimmImageSafetyModel":
        metadata = _load_metadata(path)
        weights_path = path / str(metadata["weights_file"])
        if not weights_path.is_file():
            raise ValueError(f"image-model weights are missing: {weights_path}")
        actual_sha256 = _sha256(weights_path)
        if actual_sha256 != metadata["weights_sha256"]:
            raise ValueError("image-model weight checksum does not match reviewed metadata")

        label_names = metadata["label_names"]
        raw_mapping = metadata["label_categories"]
        if not isinstance(label_names, list) or not label_names:
            raise ValueError("image-model metadata requires non-empty label_names")
        if not isinstance(raw_mapping, dict) or not raw_mapping:
            raise ValueError("image-model metadata requires a label_categories mapping")
        label_categories: dict[int, SafetyCategory] = {}
        for model_label, category in raw_mapping.items():
            if model_label not in label_names:
                raise ValueError(f"mapped model label does not exist: {model_label}")
            safety_category = SafetyCategory(category)
            if safety_category not in _SUPPORTED_CATEGORIES:
                raise ValueError(f"unsupported image category mapping: {category}")
            label_categories[label_names.index(model_label)] = safety_category

        import timm
        import torch
        from safetensors.torch import load_model

        model = timm.create_model(
            str(metadata["architecture"]),
            pretrained=False,
            num_classes=len(label_names),
        )
        load_model(model, str(weights_path), strict=True)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        model.eval()
        input_size = int(metadata["input_size"])
        transform = timm.data.create_transform(
            input_size=(3, input_size, input_size),
            is_training=False,
            mean=tuple(metadata["mean"]),
            std=tuple(metadata["std"]),
            interpolation=str(metadata.get("interpolation", "bicubic")),
            crop_pct=float(metadata.get("crop_pct", 1.0)),
        )
        return cls(
            model=model,
            transform=transform,
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

        tensor = self._transform(sanitized).unsqueeze(0).to(self._device)
        with torch.inference_mode():
            probabilities = torch.softmax(self._model(tensor), dim=-1)[0]
        scores: dict[SafetyCategory, float] = {}
        for index, category in self._label_categories.items():
            scores[category] = max(
                scores.get(category, 0.0),
                float(probabilities[index].cpu().item()),
            )
        return scores
