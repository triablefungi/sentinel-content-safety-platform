# ADR 0002: At-least-once asynchronous processing

- Status: Accepted
- Date: 2026-08-24

## Context

Sentinel needs a high-throughput path that can absorb bursts, scale consumers independently, and
recover from worker crashes. The API, Kafka, and Redis cannot be updated in one simple atomic
transaction. Claiming exactly-once processing would therefore hide important failure modes.

## Decision

Use Kafka consumer groups with automatic offset commits disabled. A worker commits a source offset
only after it has published the required downstream event and saved the corresponding Redis state.
The system exposes at-least-once delivery and uses a stable job ID plus terminal-state checks for
application-level duplicate suppression.

Bound processing to three attempts. Publish sanitized metadata to a dead-letter topic when attempts
are exhausted or an event cannot pass schema validation.

## Consequences

- A crash before commit may cause redelivery; handlers must remain idempotent.
- Kafka and Redis can temporarily disagree because there is no cross-system transaction.
- Consumers recover without silently acknowledging unfinished work.
- Operators can inspect and replay DLQ events under a controlled procedure.
- Exact-once side effects would require a transactional outbox or another coordinated design.
