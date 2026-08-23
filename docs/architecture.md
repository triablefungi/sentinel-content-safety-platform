# Architecture

## Current milestone

The service remains synchronous for the initial ML milestones. FastAPI validates a text request,
the normalization layer reduces common obfuscations, and a trie finds policy phrases. The
service prefers a fine-tuned DistilBERT classifier and falls back to TF-IDF logistic regression
when the transformer is absent. The policy engine combines those independent signals into a
versioned decision.

```mermaid
flowchart LR
    A[Client] --> B[FastAPI]
    B --> C[Normalizer]
    C --> D[Phrase trie]
    D --> E[Heuristic signals]
    C --> F[Preferred ML model]
    E --> G[Policy engine]
    F --> G
    G --> H[Decision]
```

## Target architecture

The production-oriented version separates synchronous admission from asynchronous deep
analysis. Kafka buffers submissions; horizontally scalable workers run heuristic, transformer,
and vector-retrieval stages. PostgreSQL stores decisions and policy history, while a review
queue produces labels for retraining.

Reliability requirements include idempotency keys, bounded retries, a dead-letter queue,
circuit breakers, graceful model fallback, distributed traces, and explicit error budgets.
