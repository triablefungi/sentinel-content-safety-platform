# ADR 0005: Gate model promotion on adversarial slices

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Aggregate held-out metrics do not show whether trivial text transformations cause a safety model to
miss abuse. Manually inspecting a few examples is neither reproducible nor suitable for CI.

## Decision

Maintain a versioned synthetic regression corpus, generate deterministic evasion variants, report
overall and slice metrics, and evaluate candidate model reports against version-controlled gates.
Threshold analysis remains advisory. Promotion fails closed when a required metric misses its floor.

Evaluate the deployed pipeline rather than the raw classifier: adversarial variants pass through
the versioned canonicalization boundary before inference. The model and preprocessor versions are
both recorded because changing either can change safety performance.

Raw evaluation text is kept in the corpus but omitted from generated metric artifacts. Exact model
binaries remain outside Git because of their size; the gate script operates on the report generated
from the controlled model artifact.

## Consequences

Robustness regressions become visible and machine-checkable, and model comparisons use identical
cases. However, the suite can be overfit and does not approximate the breadth of live abuse. It must
grow through reviewed incidents and red-team exercises without turning production user content into
an ungoverned benchmark.
