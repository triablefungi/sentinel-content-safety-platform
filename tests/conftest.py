from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_api_tests_from_local_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SENTINEL_MODEL_PATH", str(tmp_path / "missing-model.joblib"))
    monkeypatch.setenv(
        "SENTINEL_TRANSFORMER_MODEL_PATH",
        str(tmp_path / "missing-transformer-model"),
    )
    monkeypatch.setenv(
        "SENTINEL_IMAGE_MODEL_PATH",
        str(tmp_path / "missing-image-model"),
    )
    monkeypatch.setenv("SENTINEL_REVIEW_ENABLED", "false")
