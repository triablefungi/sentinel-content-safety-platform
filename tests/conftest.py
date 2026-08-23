from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_api_tests_from_local_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SENTINEL_MODEL_PATH", str(tmp_path / "missing-model.joblib"))
