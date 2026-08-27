# ADR 0006: Use a recall-oriented max-score ensemble

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

After canonicalization, TF-IDF at a 0.40 threshold achieved 1.000 precision, 0.653 recall, and zero
false-positive rate on the bounded adversarial suite. DistilBERT at 0.30 retained 1.000 precision
but reached only 0.583 recall. Selecting DistilBERT alone would therefore fail the versioned safety
floor even though its broader held-out Civil Comments results were stronger.

## Decision

When both artifacts are available, score canonical text with both models and use the maximum score.
Route scores from 0.40 to review and scores from 0.85 to block. This is an OR-style safety ensemble:
a signal from either detector is sufficient to intervene. Docker remains able to run the lightweight
TF-IDF model alone when the local transformer artifact is unavailable.

The adversarial evaluator reports both members and `sentinel-max-ensemble-v1` separately. CI gates
the deployed ensemble report, not an individual member.

## Consequences

This design prioritizes recall and preserves complementary detections. It also increases local
inference cost when both members are loaded and can increase false positives on broader traffic.
The current zero false-positive observation comes from only 72 transformed safe examples and is not
a production guarantee. Larger representative datasets, calibration, latency tests, and ongoing
human-review feedback are required before production deployment.
