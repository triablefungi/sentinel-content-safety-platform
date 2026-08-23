# ADR 0001: Use a layered moderation architecture

- **Status:** Accepted
- **Date:** 2026-08-23

## Context

Running the most expensive model for every submission increases latency and cost, while a
rules-only system cannot generalize to novel or obfuscated abuse.

## Decision

Sentinel will use a cascade: normalization, fast heuristics, a transformer classifier, vector
retrieval, and agentic investigation for uncertain cases. Each layer emits structured signals
that a separately versioned policy engine converts into an action.

## Consequences

- Common cases can be decided quickly.
- Expensive analysis is reserved for uncertain or severe cases.
- Decisions remain auditable because signals and policy versions are stored.
- Threshold calibration and fallback behaviour become explicit operational responsibilities.

