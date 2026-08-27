import argparse
import json
from pathlib import Path

from sentinel.evaluation.gates import check_evaluation_gates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enforce Sentinel model-promotion gates.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("artifacts/metrics/adversarial_evaluation.json"),
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=Path("config/evaluation-gates.json"),
    )
    parser.add_argument(
        "--model-version",
        help="Model version to gate; required when the report contains multiple models.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    requirements = json.loads(args.requirements.read_text(encoding="utf-8"))
    models = report["models"]
    model_version = args.model_version
    if model_version is None:
        if len(models) != 1:
            available = ", ".join(sorted(models))
            raise ValueError(f"choose --model-version from: {available}")
        model_version = next(iter(models))
    if model_version not in models:
        raise ValueError(f"model version not found in report: {model_version}")

    result = check_evaluation_gates(models[model_version], requirements)
    if not result.passed:
        print(f"Evaluation gate FAILED for {model_version}:")
        for failure in result.failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print(f"Evaluation gate PASSED for {model_version}.")


if __name__ == "__main__":
    main()
