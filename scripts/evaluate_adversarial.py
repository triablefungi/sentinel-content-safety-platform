import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sentinel.evaluation import evaluate_model, load_cases
from sentinel.evaluation.attacks import ATTACKS
from sentinel.ml.baseline import SklearnToxicityModel
from sentinel.ml.ensemble import MaxScoreToxicityEnsemble
from sentinel.ml.protocols import ToxicityModel
from sentinel.ml.transformer import TransformerToxicityModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Sentinel models against deterministic adversarial text variants."
    )
    parser.add_argument(
        "--models",
        choices=("baseline", "transformer", "both"),
        default="both",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("data/evaluation/adversarial_text_v1.jsonl"),
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=Path("artifacts/models/toxicity_baseline.joblib"),
    )
    parser.add_argument(
        "--transformer-path",
        type=Path,
        default=Path("artifacts/models/transformer_toxicity"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/metrics/adversarial_evaluation.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("docs/adversarial-evaluation-results.md"),
    )
    parser.add_argument("--threshold", type=float, default=0.4)
    return parser.parse_args()


def load_models(args: argparse.Namespace) -> list[ToxicityModel]:
    models: list[ToxicityModel] = []
    if args.models in {"baseline", "both"}:
        if not args.baseline_path.exists():
            raise FileNotFoundError(
                f"baseline model not found at {args.baseline_path}; run train_baseline.py first"
            )
        models.append(SklearnToxicityModel.load(args.baseline_path))
    if args.models in {"transformer", "both"}:
        if not args.transformer_path.exists():
            raise FileNotFoundError(
                f"transformer model not found at {args.transformer_path}; "
                "restore the trained model first"
            )
        models.append(TransformerToxicityModel.load(args.transformer_path))
    if args.models == "both":
        models.append(MaxScoreToxicityEnsemble(models))
    return models


def render_markdown(report: dict) -> str:
    lines = [
        "# Adversarial Evaluation Results",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "The synthetic corpus is a bounded engineering regression suite, not a claim of broad",
        "real-world safety coverage. Raw text is excluded from the result artifact.",
        "",
        "## Overall results",
        "",
        "| Model | Precision | Recall | F1 | FPR | Worst attack recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in report["models"].values():
        overall = model["overall"]
        robustness = model["robustness"]
        lines.append(
            f"| {model['model_version']} | {overall['precision']:.3f} | "
            f"{overall['recall']:.3f} | {overall['f1']:.3f} | "
            f"{overall['false_positive_rate']:.3f} | "
            f"{robustness['worst_attack_recall']:.3f} |"
        )
    for model in report["models"].values():
        lines.extend(
            [
                "",
                f"## Attack slices — {model['model_version']}",
                "",
                "| Attack | Precision | Recall | F1 | False negatives |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for name, metrics in model["by_attack"].items():
            lines.append(
                f"| {name} | {metrics['precision']:.3f} | {metrics['recall']:.3f} | "
                f"{metrics['f1']:.3f} | {metrics['confusion_matrix']['fn']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Threshold candidates are diagnostic. Production thresholds must be changed through",
            "a reviewed policy update, never automatically from this report.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not 0.0 < args.threshold < 1.0:
        raise ValueError("threshold must be between 0 and 1")
    cases = load_cases(args.corpus)
    model_reports = {
        model.version: evaluate_model(model, cases, threshold=args.threshold)
        for model in load_models(args)
    }
    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus": {
            "path": args.corpus.as_posix(),
            "base_cases": len(cases),
            "evaluated_variants_per_model": len(cases) * len(ATTACKS),
            "attacks": list(ATTACKS),
            "source": "synthetic-v1",
        },
        "models": model_reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")

    print(f"Evaluated {len(cases)} base cases across {len(ATTACKS)} attack families.")
    for model in model_reports.values():
        print(
            f"{model['model_version']}: precision={model['overall']['precision']:.3f}, "
            f"recall={model['overall']['recall']:.3f}, f1={model['overall']['f1']:.3f}, "
            f"worst_attack_recall={model['robustness']['worst_attack_recall']:.3f}"
        )
    print(f"JSON report saved to {args.output}")
    print(f"Markdown report saved to {args.markdown_output}")


if __name__ == "__main__":
    main()
