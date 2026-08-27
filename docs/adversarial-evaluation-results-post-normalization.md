# Adversarial Evaluation Results

Generated: `2026-08-27T09:45:12.015353+00:00`

The synthetic corpus is a bounded engineering regression suite, not a claim of broad
real-world safety coverage. Raw text is excluded from the result artifact.

## Overall results

| Model | Precision | Recall | F1 | FPR | Worst attack recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| tfidf-logreg-v1 | 1.000 | 0.569 | 0.726 | 0.000 | 0.500 |
| distilbert-toxicity-v1 | 1.000 | 0.500 | 0.667 | 0.000 | 0.500 |

## Attack slices — tfidf-logreg-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.500 | 0.667 | 6 |
| clean | 1.000 | 0.583 | 0.737 | 5 |
| leetspeak | 1.000 | 0.583 | 0.737 | 5 |
| punctuation | 1.000 | 0.583 | 0.737 | 5 |
| uppercase | 1.000 | 0.583 | 0.737 | 5 |
| zero_width | 1.000 | 0.583 | 0.737 | 5 |

## Attack slices — distilbert-toxicity-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.500 | 0.667 | 6 |
| clean | 1.000 | 0.500 | 0.667 | 6 |
| leetspeak | 1.000 | 0.500 | 0.667 | 6 |
| punctuation | 1.000 | 0.500 | 0.667 | 6 |
| uppercase | 1.000 | 0.500 | 0.667 | 6 |
| zero_width | 1.000 | 0.500 | 0.667 | 6 |

## Interpretation boundary

Threshold candidates are diagnostic. Production thresholds must be changed through
a reviewed policy update, never automatically from this report.
