# Sentinel Content Safety Platform

Sentinel is a production-oriented moderation platform for detecting harmful and adversarial
user-generated content. It is being built as an end-to-end software engineering and ML system:
from low-latency ingestion and algorithmic screening to transformer inference, vector retrieval,
human feedback, model evaluation, and reliability monitoring.

> **Current milestone:** a working FastAPI service plus a reproducible TF-IDF logistic-regression
> training pipeline using a streamed Civil Comments sample. When the trained artifact exists,
> the API combines model probabilities with heuristic safety signals.

## Why this project exists

Content-safety systems must balance user protection, model quality, latency, reliability,
fairness, and auditability. Sentinel demonstrates these trade-offs through a layered system
rather than presenting a classifier notebook as a production service.

## Current API

### `POST /v1/moderate/text`

Request:

```json
{
  "request_id": "demo-001",
  "text": "Thank you for sharing your perspective."
}
```

Response:

```json
{
  "request_id": "demo-001",
  "decision": "allow",
  "risk_score": 0.0,
  "signals": [],
  "policy_version": "2026-08-01",
  "evaluated_at": "2026-08-23T00:00:00Z"
}
```

The initial rule catalogue is deliberately small and sanitized. It exists to validate the API,
normalization, data structures, policy separation, and testing strategy before model integration.

## Run locally

### Python

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install -e ".[dev,ml]"
uvicorn sentinel.main:app --app-dir src --reload
```

Open `http://localhost:8000/docs` for the interactive API documentation.

### Docker

```bash
docker compose up --build
```

## Test and lint

```bash
pytest
ruff check .
```

## Train the ML baseline

Stream a shuffled 20,000-row sample from Civil Comments:

```bash
python scripts/download_data.py --sample-size 20000
```

Train and evaluate the baseline:

```bash
python scripts/train_baseline.py
```

This creates two local, untracked artifacts:

- `artifacts/models/toxicity_baseline.joblib`
- `artifacts/metrics/baseline_metrics.json`

Restart the API after training. It automatically loads the model and emits `ml:tfidf-logreg-v1`
signals for sufficiently high toxicity probabilities.

## Engineering roadmap

- **Milestone 1 — Foundation:** FastAPI, policy schemas, normalization, trie screening, tests,
  Docker and CI.
- **Milestone 2 — ML baseline:** Civil Comments streaming pipeline, TF-IDF logistic regression,
  model integration and binary toxicity evaluation.
- **Milestone 3 — Transformer:** fine-tune DistilBERT, calibrate thresholds, register models in
  MLflow, export an ONNX CPU model.
- **Milestone 4 — Distributed processing:** Kafka, consumer workers, idempotency, retries,
  dead-letter queues and load tests.
- **Milestone 5 — Threat intelligence:** Milvus similarity search, near-duplicate campaign
  detection and controlled agentic investigation.
- **Milestone 6 — Operations:** OpenTelemetry, Prometheus, Grafana, SLO dashboards, failure
  injection and rollback exercises.
- **Milestone 7 — Multimodal:** image safety classifier and combined text-image policy decisions.

## Initial SLO hypotheses

These are targets to validate under a documented local load-test environment, not claims of
global scale:

- 99.9% API availability during the benchmark window.
- p95 latency below 250 ms for the fast moderation path.
- At least 99.99% of accepted events reach a terminal decision or the dead-letter queue.
- No model version is promoted when a category-specific safety threshold regresses.

## Responsible development

- Public examples remain sanitized; raw harmful examples are not displayed in the README.
- Policy decisions include reason codes and policy versions for auditability.
- Evaluation will report false positives, false negatives, calibration, and subgroup behaviour.
- LLM-generated recommendations will never be the sole control for severe safety decisions.
- User content is treated as untrusted data, not as instructions to the analysis workflow.

## Repository structure

```text
src/sentinel/          Application and moderation logic
tests/                 Unit and API tests
docs/                  Architecture and decision records
.github/workflows/     Continuous integration
```

## License

MIT
