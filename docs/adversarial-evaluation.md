# Adversarial Safety Evaluation

## Purpose

Sentinel evaluates safety models against deterministic transformations that approximate simple
evasion attempts. The suite makes robustness failures measurable before a model version can be
promoted. It complements the held-out Civil Comments test split; it does not replace a larger,
independently reviewed red-team dataset.

## Corpus contract

`data/evaluation/adversarial_text_v1.jsonl` contains 24 synthetic, human-readable base cases:
12 safe and 12 unsafe. Unsafe cases cover harassment, threats, and general toxicity. Safe cases
include disagreement, criticism, quoted safety language, and benign uses of words such as
"attack" to expose false-positive risk.

Each case has a stable ID, binary intervention label, category, and provenance. The evaluator
generates six deterministic variants per case:

- clean text;
- uppercase text;
- zero-width character insertion;
- common leetspeak substitutions;
- punctuation insertion inside words; and
- character flooding.

The resulting 144 predictions per model are sufficient for a reproducible engineering regression
test, but too small and synthetic for population-level fairness or production-quality claims.

## Pre-mitigation finding

The first run intentionally evaluated raw model input and exposed a boundary mismatch. TF-IDF
achieved 0.292 recall and DistilBERT achieved 0.264 recall overall; both had zero recall on their
weakest attack slice. Leetspeak and punctuation defeated both models, while zero-width characters
defeated TF-IDF. This was not repaired by lowering the gate.

Sentinel now sends model input through `sentinel-normalization-v2`, the same canonicalization layer
used by deterministic rules and campaign encoding. The version removes zero-width separators,
reverses common leetspeak, bounds character flooding, and removes punctuation inserted inside
words. Pre- and post-mitigation reports should be retained together as engineering evidence.

## Metrics and slices

The report includes precision, recall, F1, false-positive rate, false-negative rate, and a confusion
matrix. These are calculated overall, by attack family, and by content category. Robustness is
summarized by worst-attack recall and maximum recall loss relative to clean text.

Safety metrics are reviewed together. Maximizing recall alone can make a system unusable by
over-flagging safe speech; maximizing precision alone can conceal missed abuse. The threshold table
therefore shows the trade-off without changing the production threshold automatically.

## Promotion gate

`config/evaluation-gates.json` defines explicit minimums for overall recall, precision, and
worst-attack recall, plus maximums for false-positive rate and recall degradation. Run:

```bash
python scripts/check_evaluation_gate.py --model-version distilbert-toxicity-v1
```

A non-zero exit code blocks promotion. The initial floors are engineering safeguards for this
bounded corpus, not universal safety standards. Tightening them requires a versioned configuration
change and review. A model that fails should remain available only for analysis while the current
production model stays active.

## Privacy and review boundaries

The JSON result contains IDs, labels, categories, attacks, and scores but not raw content. The
versioned corpus does contain synthetic text and must still be reviewed before public release.
Future externally sourced red-team cases require licensing, consent, access control, retention,
and annotator-wellbeing review.

## Candidate selection

Threshold analysis showed that TF-IDF at 0.40 met the initial recall floor with no observed false
positives, while DistilBERT remained below the floor even at 0.30. Because the models have
complementary strengths, the deployed candidate is `sentinel-max-ensemble-v1`: the maximum member
score is compared with the reviewed 0.40 intervention threshold. CI gates the ensemble while still
reporting both members independently. See
[`ADR 0006`](adr/0006-recall-oriented-model-ensemble.md) for the decision and limitations.

## Known limitations

- The corpus is English-only and does not measure multilingual performance.
- It does not measure protected-group fairness or dialect performance.
- Deterministic attacks do not represent adaptive adversaries.
- Binary toxicity labels collapse policy distinctions and context.
- Small slices produce unstable estimates and no confidence intervals.
- The suite does not validate image, audio, or cross-modal safety.
