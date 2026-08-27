import hashlib
import json

import pytest

from sentinel.multimodal.timm_model import TimmImageSafetyModel, _load_metadata
from sentinel.schemas.moderation import SafetyCategory


def _metadata(checksum: str = "0" * 64) -> dict[str, object]:
    return {
        "model_version": "image-safety-test-v1",
        "backend": "timm-safetensors",
        "architecture": "swiftformer_l1",
        "weights_file": "model.safetensors",
        "weights_sha256": checksum,
        "label_names": ["NSFL", "NSFW", "SFW"],
        "label_categories": {
            "NSFL": "graphic_violence",
            "NSFW": "sexual_content",
        },
        "input_size": 224,
        "mean": [0.485, 0.456, 0.406],
        "std": [0.229, 0.224, 0.225],
    }


def test_timm_adapter_exposes_reviewed_version() -> None:
    adapter = TimmImageSafetyModel(
        model=object(),
        transform=object(),
        device="cpu",
        version="image-safety-test-v1",
        label_categories={0: SafetyCategory.GRAPHIC_VIOLENCE},
    )

    assert adapter.version == "image-safety-test-v1"


def test_metadata_requires_reviewed_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    metadata = _metadata()
    metadata["backend"] = "remote-code"
    (tmp_path / "sentinel_image_metadata.json").write_text(json.dumps(metadata))

    with pytest.raises(ValueError, match="unsupported image-model backend"):
        _load_metadata(tmp_path)


def test_load_rejects_missing_weights_before_importing_model_stack(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "sentinel_image_metadata.json").write_text(json.dumps(_metadata()))

    with pytest.raises(ValueError, match="weights are missing"):
        TimmImageSafetyModel.load(tmp_path)


def test_load_rejects_unreviewed_weight_checksum_before_importing_model_stack(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    weights = tmp_path / "model.safetensors"
    weights.write_bytes(b"not-reviewed-weights")
    expected = hashlib.sha256(b"different-weights").hexdigest()
    (tmp_path / "sentinel_image_metadata.json").write_text(
        json.dumps(_metadata(expected))
    )

    with pytest.raises(ValueError, match="checksum does not match"):
        TimmImageSafetyModel.load(tmp_path)
