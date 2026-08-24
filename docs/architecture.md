# Architecture

## Current architecture

Sentinel exposes both a synchronous decision path and an asynchronous job path. The moderation
engine is shared: FastAPI validates text, normalization reduces common obfuscations, and a trie
finds policy phrases. The service prefers a fine-tuned DistilBERT classifier, falls back to TF-IDF
logistic regression, and combines the selected model with heuristic and vector-campaign signals.

```mermaid
flowchart LR
    A[Client] --> B[FastAPI]
    B -->|synchronous| C[Normalizer]
    C --> D[Phrase trie]
    D --> E[Heuristic signals]
    C --> F[Preferred ML model]
    C --> Q[(Qdrant)]
    Q --> T[Campaign signal]
    E --> G[Policy engine]
    F --> G
    T --> G
    G --> H[Decision]
    B -->|asynchronous| K[(Kafka)]
    K --> W[Worker group]
    W --> C
    B --> R[(Redis job state)]
    W --> R
```

See [Distributed moderation architecture](distributed-architecture.md) for delivery semantics,
idempotency, retries, the dead-letter queue, and local operation. See
[Threat-intelligence architecture](threat-intelligence-architecture.md) for vector retrieval,
campaign thresholds, and the data-minimization boundary.

## Next architecture increments

Kafka buffers submissions and worker replicas can join one consumer group. Qdrant now retrieves
near-duplicate content vectors and raises coordinated-campaign signals. Future increments add
PostgreSQL decision history and a review queue that produces controlled feedback for retraining.

Implemented reliability controls include idempotency keys, bounded retries, a dead-letter queue,
explicit offset commits, and graceful model fallback. Circuit breakers, distributed traces,
failure injection, and explicit error-budget dashboards remain planned.
