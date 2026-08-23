import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from datasets import Dataset
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

MODEL_VERSION = "distilbert-toxicity-v1"


class WeightedTrainer(Trainer):
    """Trainer using class-weighted cross entropy for imbalanced safety labels."""

    def __init__(self, *args: Any, class_weights: np.ndarray, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._class_weights = torch.tensor(class_weights, dtype=torch.float32)

    def compute_loss(
        self,
        model: torch.nn.Module,
        inputs: dict[str, torch.Tensor],
        return_outputs: bool = False,
        num_items_in_batch: torch.Tensor | None = None,
    ) -> torch.Tensor | tuple[torch.Tensor, Any]:
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        loss_function = torch.nn.CrossEntropyLoss(
            weight=self._class_weights.to(outputs.logits.device)
        )
        loss = loss_function(outputs.logits, labels)
        return (loss, outputs) if return_outputs else loss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune DistilBERT for toxicity detection.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/civil_comments_sample.csv"),
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=Path("artifacts/models/transformer_toxicity"),
    )
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=Path("artifacts/metrics/transformer_metrics.json"),
    )
    parser.add_argument(
        "--checkpoint",
        default="distilbert/distilbert-base-uncased",
    )
    parser.add_argument("--epochs", type=float, default=2.0)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def probabilities_from_logits(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials[:, 1] / exponentials.sum(axis=1)


def calculate_metrics(logits: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    probabilities = probabilities_from_logits(logits)
    predictions = (probabilities >= 0.5).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="binary",
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
    }


def main() -> None:
    args = parse_args()
    frame = pd.read_csv(args.input).dropna(subset=["text", "label"])
    train_frame, test_frame = train_test_split(
        frame[["text", "label"]],
        test_size=0.20,
        random_state=args.seed,
        stratify=frame["label"],
    )
    train_frame = train_frame.reset_index(drop=True)
    test_frame = test_frame.reset_index(drop=True)

    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.checkpoint,
        num_labels=2,
        id2label={0: "NON_TOXIC", 1: "TOXIC"},
        label2id={"NON_TOXIC": 0, "TOXIC": 1},
    )

    train_dataset = Dataset.from_pandas(train_frame, preserve_index=False)
    test_dataset = Dataset.from_pandas(test_frame, preserve_index=False)

    def tokenize(batch: dict[str, list[Any]]) -> dict[str, Any]:
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_length,
        )

    tokenized_train = train_dataset.map(tokenize, batched=True, remove_columns=["text"])
    tokenized_test = test_dataset.map(tokenize, batched=True, remove_columns=["text"])
    class_weights = compute_class_weight(
        class_weight="balanced",
        classes=np.array([0, 1]),
        y=train_frame["label"].astype(int).to_numpy(),
    )

    training_arguments = TrainingArguments(
        output_dir=str(args.model_output.parent / "transformer_checkpoints"),
        learning_rate=2e-5,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        warmup_ratio=0.10,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        report_to="none",
        fp16=torch.cuda.is_available(),
        seed=args.seed,
        data_seed=args.seed,
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_arguments,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_test,
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=lambda prediction: calculate_metrics(
            prediction.predictions,
            prediction.label_ids,
        ),
        class_weights=class_weights,
    )
    trainer.train()

    prediction_output = trainer.predict(tokenized_test)
    final_metrics = calculate_metrics(
        prediction_output.predictions,
        prediction_output.label_ids,
    )
    probabilities = probabilities_from_logits(prediction_output.predictions)
    predictions = (probabilities >= 0.5).astype(int)
    final_metrics.update(
        {
            "model_version": MODEL_VERSION,
            "base_checkpoint": args.checkpoint,
            "trained_at": datetime.now(UTC).isoformat(),
            "dataset_rows": int(len(frame)),
            "train_rows": int(len(train_frame)),
            "test_rows": int(len(test_frame)),
            "decision_threshold": 0.5,
            "confusion_matrix": confusion_matrix(
                prediction_output.label_ids,
                predictions,
            ).tolist(),
        }
    )

    baseline_path = Path("artifacts/metrics/baseline_metrics.json")
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_toxic = baseline["classification_report"]["toxic"]
        final_metrics["improvement_over_baseline"] = {
            "precision_delta": final_metrics["precision"] - baseline_toxic["precision"],
            "recall_delta": final_metrics["recall"] - baseline_toxic["recall"],
            "f1_delta": final_metrics["f1"] - baseline_toxic["f1-score"],
            "roc_auc_delta": final_metrics["roc_auc"] - baseline["roc_auc"],
        }

    args.model_output.mkdir(parents=True, exist_ok=True)
    trainer.save_model(args.model_output)
    tokenizer.save_pretrained(args.model_output)
    (args.model_output / "sentinel_metadata.json").write_text(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "max_length": args.max_length,
                "base_checkpoint": args.checkpoint,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_output.write_text(json.dumps(final_metrics, indent=2), encoding="utf-8")

    print(f"Model saved to {args.model_output}")
    print(f"Metrics saved to {args.metrics_output}")
    print(f"Toxic precision: {final_metrics['precision']:.3f}")
    print(f"Toxic recall: {final_metrics['recall']:.3f}")
    print(f"Toxic F1: {final_metrics['f1']:.3f}")
    print(f"ROC-AUC: {final_metrics['roc_auc']:.3f}")


if __name__ == "__main__":
    main()
