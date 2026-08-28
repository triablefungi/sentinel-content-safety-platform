# ADR 0009: Append-only human-review ledger

- Status: accepted
- Date: 2026-08-28

## Context

Automated safety decisions need accountable human intervention, appeals, and feedback without
turning operational telemetry into a second store of user content. Reviewer actions must be
traceable, stale transitions must fail, and model retraining must not silently consume raw data.

## Decision

Represent review as an explicit state machine backed by a hash-chained append-only JSONL ledger.
Store identifiers and decision metadata only. Authenticate reviewers with hashed bearer tokens and
enforce reviewer, senior-reviewer, and auditor roles. Export only resolved label metadata; raw
content joins remain a separate governed process.

## Consequences

- Every claim, decision, appeal, and appeal decision is attributable and ordered.
- Ledger corruption or sequence breaks fail startup instead of being silently ignored.
- Raw user content is absent from the review ledger and feedback export.
- The local file repository is intentionally single-process and unsuitable for horizontal writes.
- Production requires transactional persistence, centralized identity, retention enforcement, and
  a controlled content-viewing system.
