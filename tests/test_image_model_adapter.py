import pytest

from sentinel.multimodal.transformer import TransformerImageSafetyModel
from sentinel.schemas.moderation import SafetyCategory


def test_image_adapter_exposes_reviewed_version() -> None:
    adapter = TransformerImageSafetyModel(
        model=object(),
        processor=object(),
        device="cpu",
        version="image-safety-test-v1",
        label_categories={0: SafetyCategory.SEXUAL_CONTENT},
    )

    assert adapter.version == "image-safety-test-v1"


def test_image_adapter_constructor_keeps_category_mapping() -> None:
    adapter = TransformerImageSafetyModel(
        model=object(),
        processor=object(),
        device="cpu",
        version="image-safety-test-v1",
        label_categories={1: SafetyCategory.GRAPHIC_VIOLENCE},
    )

    assert adapter._label_categories == {1: SafetyCategory.GRAPHIC_VIOLENCE}


def test_image_adapter_rejects_missing_metadata_before_loading_dependencies(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="metadata is missing"):
        TransformerImageSafetyModel.load(tmp_path)
