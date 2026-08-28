# Ten-minute demonstration guide

## 1. Frame the problem (one minute)

Sentinel is a layered content-safety platform, not a standalone classifier. It combines fast
policy checks, two text models, secure image moderation, campaign intelligence, distributed
processing, human review, and SLO-driven operations.

## 2. Show engineering quality (one minute)

```bash
python -m pytest
python -m ruff check .
python scripts/check_security_configuration.py
```

Point out the deterministic adversarial promotion gate, 80% overall coverage, lockfile-derived
CycloneDX SBOM, CodeQL workflow, and Dependabot configuration.

## 3. Start and inspect the platform (two minutes)

```bash
docker compose up -d --build
docker compose ps -a
python scripts/verify_observability.py
python scripts/verify_production_controls.py
```

Explain that Kafka provides durable at-least-once delivery, Redis stores idempotent job state,
Qdrant detects coordinated near-duplicates, and the API/worker expose separate metrics.

## 4. Demonstrate safety decisions (two minutes)

Use `/docs` locally to submit one benign message, one toxic message, and one valid multimodal
request. Show the returned policy version, decision, bounded risk signal, and correlation header.
Then show that a declared JPEG carrying PNG bytes is rejected.

## 5. Demonstrate accountable escalation (two minutes)

```bash
python scripts/verify_review_workflow.py
```

Explain `pending → claimed → resolved → appealed → claimed → resolved`, senior-review separation,
the six hash-chained audit events, and why raw content is excluded from the feedback export.

## 6. Close with operations and trade-offs (two minutes)

Open Prometheus and Grafana. Show latency, throughput, DLQ, worker outcomes and review backlog.
State the important limitations: local synthetic evaluation, a single-node Compose environment,
an in-process rate limiter, a JSONL ledger, and a candidate—not production-approved—vision model.
Then explain the documented production replacements in `docs/deployment.md`.
