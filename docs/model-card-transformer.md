# Model Card: DistilBERT Toxicity Classifier

## Model details

- **Model version:** `distilbert-toxicity-v1`
- **Base checkpoint:** `distilbert/distilbert-base-uncased`
- **Task:** binary English-text toxicity classification
- **Architecture:** six-layer distilled transformer encoder with a sequence-classification head
- **Maximum sequence length:** 256 tokens
- **Decision threshold:** 0.50
- **Training workflow:** `scripts/train_transformer.py`
- **Runtime adapter:** `src/sentinel/ml/transformer.py`

The classifier is one signal in Sentinel's layered moderation system. Deterministic phrase rules,
normalization, the selected ML model, and a versioned policy engine jointly produce the final
allow, review, or block decision.

## Intended use

This model is intended for portfolio-scale experimentation with English user-generated text. It
can prioritize potentially toxic content for review and demonstrate model training, evaluation,
versioning, and production integration.

It is not approved for autonomous enforcement, high-stakes decisions, or deployment without
additional policy, fairness, calibration, privacy, security, and operational evaluation.

## Training data

The training workflow streams a reproducible 20,000-row sample from Civil Comments. A comment is
labelled toxic when its source toxicity score is at least 0.50.

- Training rows: 16,000
- Test rows: 4,000
- Positive-label rate: approximately 7.75%
- Split: stratified 80/20 split with random seed 42
- Imbalance handling: class-weighted cross entropy
- Epochs: 2
- Training hardware: NVIDIA T4 GPU

The model inherits the dataset's annotation choices, historical context, language distribution,
and representation gaps.

## Evaluation

The transformer and TF-IDF baseline were evaluated on the same held-out split.

| Metric | TF-IDF baseline | DistilBERT |
| --- | ---: | ---: |
| Accuracy | 0.917 | 0.941 |
| Toxic precision | 0.464 | 0.609 |
| Toxic recall | 0.461 | 0.648 |
| Toxic F1 | 0.463 | 0.628 |
| ROC-AUC | 0.843 | 0.934 |
| Average precision | 0.474 | 0.695 |

DistilBERT confusion matrix, ordered as `[[TN, FP], [FN, TP]]`:

```text
[[3561, 129],
 [ 109, 201]]
```

Compared with the baseline, the transformer reduced false positives from 165 to 129 and false
negatives from 167 to 109. The raw evaluation record is stored at
`artifacts/metrics/transformer_metrics.json`.

## Limitations and risks

- The evaluation covers one relatively small held-out sample and does not establish global-scale
  performance.
- The binary toxicity label collapses distinct harms such as harassment, threats, hate, sexual
  content, and self-harm into a single score.
- The model may mishandle quotation, counterspeech, reclaimed language, sarcasm, coded language,
  multilingual text, and new adversarial phrasing.
- Identity terms may correlate with labels in the source dataset, creating subgroup disparities.
- Inputs longer than 256 tokens are truncated and may lose decisive context.
- A fixed 0.50 model threshold is not calibrated to a production cost model or category-specific
  policy.
- Confident model output does not guarantee factual or policy correctness.

## Responsible deployment requirements

Before production use, evaluate subgroup error rates, multilingual and adversarial test suites,
probability calibration, category-specific thresholds, latency, drift, privacy controls, and
human-review capacity. Severe decisions should retain an auditable policy version, reason codes,
appeal paths, and rollback mechanisms.

## Reproducibility

Run the Colab notebook at `notebooks/sentinel_transformer_training_colab.ipynb`. The generated
model is intentionally excluded from Git because of its size. The training script, architecture
notes, model metadata, and evaluation metrics remain versioned for review.
