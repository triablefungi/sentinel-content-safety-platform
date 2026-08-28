# Portfolio summary

## One-line description

Built a production-oriented Python content-safety platform spanning multimodal ML inference,
distributed processing, coordinated-abuse detection, human review, adversarial evaluation,
observability, and security hardening.

## Resume-ready bullets

- Designed FastAPI moderation APIs and a Kafka/Redis worker pipeline with deterministic
  idempotency, bounded retries, dead-letter handling, and outage recovery.
- Integrated TF-IDF and fine-tuned DistilBERT classifiers with recall-oriented ensemble policy,
  adversarial slice evaluation, and automated model-promotion gates.
- Added secure image ingestion and reviewed vision-model inference, validating signatures,
  dimensions, pixel limits, animation and cross-modal disagreements before policy fusion.
- Implemented Qdrant-based near-duplicate campaign detection with privacy-conscious vector
  metadata and risk escalation from allow to review to block.
- Built an authenticated human-review and appeals workflow with role separation, a tamper-evident
  audit chain, privacy-safe feedback export, and backlog monitoring.
- Defined Prometheus/Grafana SLOs and runbooks; locally validated 100/100 asynchronous completions,
  164 submissions/s, worker-outage recovery, and persistent review-state recovery.
- Hardened the API and container with request limits, rate limiting, security headers, non-root
  execution, read-only filesystems, dropped capabilities, CodeQL, Dependabot, and a reproducible
  CycloneDX SBOM.

## Interview discussion points

- Why at-least-once delivery requires idempotent processing and explicit commit boundaries.
- Why high overall accuracy can conceal unsafe false negatives and why slice-level recall matters.
- Why image bytes, user text, request IDs and reviewer notes have different telemetry boundaries.
- Why local token buckets and JSONL ledgers are suitable demonstrations but not multi-replica
  production controls.
- How SLOs, error budgets, human escalation and rollback evidence turn a model into an accountable
  safety system.
