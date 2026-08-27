import pytest

from sentinel.evaluation.attacks import clean
from sentinel.evaluation.cases import EvaluationCase
from sentinel.evaluation.metrics import ScoredCase, binary_metrics, evaluate_model, evaluate_scores


class KeywordModel:
    @property
    def version(self) -> str:
        return "keyword-test-v1"

    def predict_score(self, text: str) -> float:
        return 0.9 if "unsafe" in text.casefold() else 0.1


def test_binary_metrics_calculates_confusion_rates() -> None:
    metrics = binary_metrics([0, 0, 1, 1], [0.1, 0.8, 0.7, 0.2], threshold=0.5)

    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["false_positive_rate"] == pytest.approx(0.5)
    assert metrics["confusion_matrix"] == {"tn": 1, "fp": 1, "fn": 1, "tp": 1}


def test_evaluate_model_reports_attack_and_category_slices() -> None:
    cases = [
        EvaluationCase("safe-1", "safe", 0, "safe", "test"),
        EvaluationCase("unsafe-1", "unsafe", 1, "toxicity", "test"),
    ]

    report = evaluate_model(KeywordModel(), cases)

    assert report["overall"]["examples"] == 12
    assert report["overall"]["f1"] == pytest.approx(1.0)
    assert report["preprocessor_version"] == "sentinel-normalization-v2"
    assert set(report["by_attack"]) == {
        "character_flooding",
        "clean",
        "leetspeak",
        "punctuation",
        "uppercase",
        "zero_width",
    }
    assert set(report["by_category"]) == {"safe", "toxicity"}
    assert all("text" not in prediction for prediction in report["predictions"])


def test_robustness_exposes_worst_attack_recall() -> None:
    scored = [
        ScoredCase("unsafe-1", 1, "toxicity", "clean", 0.9),
        ScoredCase("safe-1", 0, "safe", "clean", 0.1),
        ScoredCase("unsafe-1", 1, "toxicity", "evasion", 0.2),
        ScoredCase("safe-1", 0, "safe", "evasion", 0.1),
    ]

    report = evaluate_scores("test-v1", scored)

    assert report["robustness"]["clean_recall"] == pytest.approx(1.0)
    assert report["robustness"]["worst_attack_recall"] == pytest.approx(0.0)
    assert report["robustness"]["maximum_recall_drop_from_clean"] == pytest.approx(1.0)


def test_invalid_model_probability_is_rejected() -> None:
    class InvalidModel(KeywordModel):
        def predict_score(self, text: str) -> float:
            return 1.1

    cases = [
        EvaluationCase("safe-1", "safe", 0, "safe", "test"),
        EvaluationCase("unsafe-1", "unsafe", 1, "toxicity", "test"),
    ]

    with pytest.raises(ValueError, match="within"):
        evaluate_model(InvalidModel(), cases, attacks={"clean": clean})
