# ADR 0003: Use Qdrant behind a vector-store interface for campaign detection

## Status

Accepted

## Context

The existing rule and ML layers score one message at a time. They cannot detect a repeated payload
distributed across many requests, a common abuse and virality pattern. The project needs local
vector retrieval without coupling moderation policy to one database client.

## Decision

Use Qdrant as the Docker Compose vector service and isolate it behind `ThreatVectorStore`. Use a
deterministic hashed character n-gram encoder for the first implementation. Search before upsert,
count distinct request IDs, and emit a policy signal after two prior matches. Store only the vector
and request identifier in Qdrant payloads.

## Consequences

- The pipeline demonstrates vector retrieval and campaign-level reasoning with reproducible CPU
  inference and no external embedding API.
- Unit tests can use an in-memory cosine store while deployment uses Qdrant.
- The encoder is effective for near-duplicates and simple obfuscation, not semantic equivalence.
- Qdrant becomes a service dependency when threat intelligence is enabled and needs its own
  security, retention, availability, backup, and capacity controls.
- Thresholds require offline calibration and monitoring before any production use.
