import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """One versioned, human-reviewed adversarial evaluation example."""

    case_id: str
    text: str
    label: int
    category: str
    source: str

    @classmethod
    def from_mapping(cls, value: dict[str, object]) -> "EvaluationCase":
        required = {"case_id", "text", "label", "category", "source"}
        missing = required.difference(value)
        if missing:
            raise ValueError(f"evaluation case is missing fields: {sorted(missing)}")
        label = value["label"]
        if label not in (0, 1):
            raise ValueError("evaluation label must be 0 or 1")
        text = str(value["text"]).strip()
        if not text:
            raise ValueError("evaluation text must not be blank")
        return cls(
            case_id=str(value["case_id"]),
            text=text,
            label=int(label),
            category=str(value["category"]),
            source=str(value["source"]),
        )


def load_cases(path: Path) -> list[EvaluationCase]:
    """Load JSON Lines cases and reject duplicate identifiers."""
    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = EvaluationCase.from_mapping(json.loads(line))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid evaluation case on line {line_number}: {error}") from error
        if case.case_id in seen_ids:
            raise ValueError(f"duplicate evaluation case_id: {case.case_id}")
        seen_ids.add(case.case_id)
        cases.append(case)
    if not cases:
        raise ValueError("evaluation corpus must contain at least one case")
    if {case.label for case in cases} != {0, 1}:
        raise ValueError("evaluation corpus must contain both safe and unsafe cases")
    return cases
