from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass

from sentinel.core.normalization import NORMALIZATION_VERSION, normalize_text
from sentinel.evaluation.attacks import ATTACKS, Attack
from sentinel.evaluation.cases import EvaluationCase
from sentinel.ml.protocols import ToxicityModel


@dataclass(frozen=True, slots=True)
class ScoredCase:
    case_id: str
    label: int
    category: str
    attack: str
    score: float


def binary_metrics(labels: Sequence[int], scores: Sequence[float], threshold: float) -> dict:
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must be non-empty and equal in length")
    predictions = [int(score >= threshold) for score in scores]
    pairs = list(zip(labels, predictions, strict=True))
    tp = sum(label == 1 and prediction == 1 for label, prediction in pairs)
    tn = sum(label == 0 and prediction == 0 for label, prediction in pairs)
    fp = sum(label == 0 and prediction == 1 for label, prediction in pairs)
    fn = sum(label == 1 and prediction == 0 for label, prediction in pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "examples": len(labels),
        "threshold": threshold,
        "accuracy": (tp + tn) / len(labels),
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "false_negative_rate": fn / (fn + tp) if fn + tp else 0.0,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def _slice_metrics(
    scored: Iterable[ScoredCase],
    attribute: str,
    threshold: float,
) -> dict[str, dict]:
    groups: dict[str, list[ScoredCase]] = defaultdict(list)
    for item in scored:
        groups[str(getattr(item, attribute))].append(item)
    return {
        name: binary_metrics(
            [item.label for item in items],
            [item.score for item in items],
            threshold,
        )
        for name, items in sorted(groups.items())
    }


def evaluate_scores(
    model_version: str,
    scored: Sequence[ScoredCase],
    threshold: float = 0.4,
    threshold_candidates: Sequence[float] = (0.3, 0.4, 0.5, 0.6, 0.7),
) -> dict:
    labels = [item.label for item in scored]
    scores = [item.score for item in scored]
    attack_slices = _slice_metrics(scored, "attack", threshold)
    clean_recall = attack_slices["clean"]["recall"]
    attacked_recalls = [
        metrics["recall"] for name, metrics in attack_slices.items() if name != "clean"
    ]
    return {
        "model_version": model_version,
        "preprocessor_version": NORMALIZATION_VERSION,
        "decision_threshold": threshold,
        "overall": binary_metrics(labels, scores, threshold),
        "by_attack": attack_slices,
        "by_category": _slice_metrics(scored, "category", threshold),
        "robustness": {
            "clean_recall": clean_recall,
            "worst_attack_recall": min(attacked_recalls, default=clean_recall),
            "maximum_recall_drop_from_clean": max(
                (clean_recall - recall for recall in attacked_recalls),
                default=0.0,
            ),
        },
        "threshold_analysis": [
            binary_metrics(labels, scores, candidate) for candidate in threshold_candidates
        ],
        "predictions": [asdict(item) for item in scored],
    }


def evaluate_model(
    model: ToxicityModel,
    cases: Sequence[EvaluationCase],
    threshold: float = 0.4,
    attacks: Mapping[str, Attack] = ATTACKS,
) -> dict:
    scored: list[ScoredCase] = []
    for case in cases:
        for attack_name, attack in attacks.items():
            transformed_text = attack(case.text)
            canonical_text = normalize_text(transformed_text)
            score = float(model.predict_score(canonical_text))
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"model score must be within [0, 1], got {score}")
            scored.append(
                ScoredCase(
                    case_id=case.case_id,
                    label=case.label,
                    category=case.category,
                    attack=attack_name,
                    score=score,
                )
            )
    report = evaluate_scores(model.version, scored, threshold=threshold)
    member_versions = getattr(model, "member_versions", None)
    if member_versions is not None:
        report["member_versions"] = list(member_versions)
    return report
