# Adversarial Evaluation Results

Generated: `2026-08-27T09:39:49.524462+00:00`

The synthetic corpus is a bounded engineering regression suite, not a claim of broad
real-world safety coverage. Raw text is excluded from the result artifact.

## Overall results

| Model | Precision | Recall | F1 | FPR | Worst attack recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| tfidf-logreg-v1 | 0.955 | 0.292 | 0.447 | 0.014 | 0.000 |
| distilbert-toxicity-v1 | 1.000 | 0.264 | 0.418 | 0.000 | 0.000 |

## Attack slices — tfidf-logreg-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 0.875 | 0.583 | 0.700 | 5 |
| clean | 1.000 | 0.583 | 0.737 | 5 |
| leetspeak | 0.000 | 0.000 | 0.000 | 12 |
| punctuation | 0.000 | 0.000 | 0.000 | 12 |
| uppercase | 1.000 | 0.583 | 0.737 | 5 |
| zero_width | 0.000 | 0.000 | 0.000 | 12 |

## Attack slices — distilbert-toxicity-v1

| Attack | Precision | Recall | F1 | False negatives |
| --- | ---: | ---: | ---: | ---: |
| character_flooding | 1.000 | 0.083 | 0.154 | 11 |
| clean | 1.000 | 0.500 | 0.667 | 6 |
| leetspeak | 0.000 | 0.000 | 0.000 | 12 |
| punctuation | 0.000 | 0.000 | 0.000 | 12 |
| uppercase | 1.000 | 0.500 | 0.667 | 6 |
| zero_width | 1.000 | 0.500 | 0.667 | 6 |

## Interpretation boundary

Threshold candidates are diagnostic. Production thresholds must be changed through
a reviewed policy update, never automatically from this report.
