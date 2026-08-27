from sentinel.evaluation.gates import check_evaluation_gates

REQUIREMENTS = {
    "minimum_overall_recall": 0.60,
    "minimum_overall_precision": 0.60,
    "minimum_worst_attack_recall": 0.30,
    "maximum_false_positive_rate": 0.25,
    "maximum_recall_drop_from_clean": 0.50,
}


def passing_report() -> dict:
    return {
        "overall": {"recall": 0.8, "precision": 0.9, "false_positive_rate": 0.1},
        "robustness": {"worst_attack_recall": 0.7, "maximum_recall_drop_from_clean": 0.2},
    }


def test_gate_passes_report_meeting_every_floor() -> None:
    result = check_evaluation_gates(passing_report(), REQUIREMENTS)

    assert result.passed
    assert result.failures == ()


def test_gate_reports_each_failed_requirement() -> None:
    report = passing_report()
    report["overall"]["recall"] = 0.2
    report["robustness"]["worst_attack_recall"] = 0.1

    result = check_evaluation_gates(report, REQUIREMENTS)

    assert not result.passed
    assert len(result.failures) == 2
    assert "overall recall" in result.failures[0]
