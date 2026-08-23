import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the TF-IDF toxicity baseline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/civil_comments_sample.csv"),
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("artifacts/models/toxicity_baseline.joblib"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("artifacts/metrics/baseline_metrics.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(args.input).dropna(subset=["text", "label"])
    if frame["label"].nunique() != 2:
        raise ValueError("training data must contain both toxic and non-toxic examples")

    x_train, x_test, y_train, y_test = train_test_split(
        frame["text"],
        frame["label"].astype(int),
        test_size=0.20,
        random_state=args.seed,
        stratify=frame["label"],
    )

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=50_000,
                    sublinear_tf=True,
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1_000,
                    solver="liblinear",
                    random_state=args.seed,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)

    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    report = classification_report(
        y_test,
        predictions,
        target_names=["non_toxic", "toxic"],
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "model_version": "tfidf-logreg-v1",
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset_rows": int(len(frame)),
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "decision_threshold": 0.5,
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": report,
    }

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "metadata": {
                "model_version": metrics["model_version"],
                "trained_at": metrics["trained_at"],
                "decision_threshold": metrics["decision_threshold"],
            },
        },
        args.model_output,
    )
    args.metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    toxic_metrics = report["toxic"]
    print(f"Model saved to {args.model_output}")
    print(f"Metrics saved to {args.metrics_output}")
    print(f"Toxic precision: {toxic_metrics['precision']:.3f}")
    print(f"Toxic recall: {toxic_metrics['recall']:.3f}")
    print(f"Toxic F1: {toxic_metrics['f1-score']:.3f}")
    print(f"ROC-AUC: {metrics['roc_auc']:.3f}")


if __name__ == "__main__":
    main()

