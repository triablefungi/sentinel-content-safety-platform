# Adversarial Evaluation Results

Generated: `2026-08-27T09:49:51.062057+00:00`

The synthetic corpus is a bounded engineering regression suite, not a claim of broad
real-world safety coverage. Raw text is excluded from the result artifact.

## Overall results

| Model | Precision | Recall | F1 | FPR | Worst attack recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| tfidf-logreg-v1 | 1.000 | 0.653 | 0.790 | 0.000 | 0.583 |
| distilbert-toxicity-v1 | 1.000 | 0.500 | 0.667 | 0.000 | 0.500 |
| sentinel-max-ensemble-v1 | 1.000 | 0.667 | 0.800 | 0.000 | 0.667 |

## Attack slices — tfidf-logreg-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.583 | 0.737 | 5 |
| clean | 1.000 | 0.667 | 0.800 | 4 |
| leetspeak | 1.000 | 0.667 | 0.800 | 4 |
| punctuation | 1.000 | 0.667 | 0.800 | 4 |
| uppercase | 1.000 | 0.667 | 0.800 | 4 |
| zero_width | 1.000 | 0.667 | 0.800 | 4 |

## Attack slices — distilbert-toxicity-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.500 | 0.667 | 6 |
| clean | 1.000 | 0.500 | 0.667 | 6 |
| leetspeak | 1.000 | 0.500 | 0.667 | 6 |
| punctuation | 1.000 | 0.500 | 0.667 | 6 |
| uppercase | 1.000 | 0.500 | 0.667 | 6 |
| zero_width | 1.000 | 0.500 | 0.667 | 6 |

## Attack slices — sentinel-max-ensemble-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.667 | 0.800 | 4 |
| clean | 1.000 | 0.667 | 0.800 | 4 |
| leetspeak | 1.000 | 0.667 | 0.800 | 4 |
| punctuation | 1.000 | 0.667 | 0.800 | 4 |
| uppercase | 1.000 | 0.667 | 0.800 | 4 |
| zero_width | 1.000 | 0.667 | 0.800 | 4 |

## Interpretation boundary

Threshold candidates are diagnostic. Production thresholds must be changed through
a reviewed policy update, never automatically from this report.
