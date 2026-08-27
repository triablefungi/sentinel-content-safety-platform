from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GateResult:
    passed: bool
    failures: tuple[str, ...]


def check_evaluation_gates(report: dict, requirements: dict) -> GateResult:
    """Apply explicit model-promotion floors to one model evaluation report."""
    overall = report["overall"]
    robustness = report["robustness"]
    checks = (
        (
            overall["recall"] >= requirements["minimum_overall_recall"],
            "overall recall",
            overall["recall"],
            requirements["minimum_overall_recall"],
            ">=",
        ),
        (
            overall["precision"] >= requirements["minimum_overall_precision"],
            "overall precision",
            overall["precision"],
            requirements["minimum_overall_precision"],
            ">=",
        ),
        (
            robustness["worst_attack_recall"]
            >= requirements["minimum_worst_attack_recall"],
            "worst attack recall",
            robustness["worst_attack_recall"],
            requirements["minimum_worst_attack_recall"],
            ">=",
        ),
        (
            overall["false_positive_rate"]
            <= requirements["maximum_false_positive_rate"],
            "false positive rate",
            overall["false_positive_rate"],
            requirements["maximum_false_positive_rate"],
            "<=",
        ),
        (
            robustness["maximum_recall_drop_from_clean"]
            <= requirements["maximum_recall_drop_from_clean"],
            "maximum recall drop from clean",
            robustness["maximum_recall_drop_from_clean"],
            requirements["maximum_recall_drop_from_clean"],
            "<=",
        ),
    )
    failures = tuple(
        f"{name} {actual:.3f} must be {operator} {expected:.3f}"
        for passed, name, actual, expected, operator in checks
        if not passed
    )
    return GateResult(passed=not failures, failures=failures)
