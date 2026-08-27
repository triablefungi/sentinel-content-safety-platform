import json
from pathlib import Path

import pytest

from sentinel.evaluation.cases import load_cases


def test_load_cases_requires_balanced_label_presence(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps(
            {
                "case_id": "safe-1",
                "text": "A safe example.",
                "label": 0,
                "category": "safe",
                "source": "test",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="both safe and unsafe"):
        load_cases(path)


def test_load_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    values = [
        {"case_id": "same", "text": "Safe.", "label": 0, "category": "safe", "source": "test"},
        {
            "case_id": "same",
            "text": "Unsafe.",
            "label": 1,
            "category": "toxicity",
            "source": "test",
        },
    ]
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(value) for value in values), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)
