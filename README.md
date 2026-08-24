# Sentinel Content Safety Platform

Sentinel is a production-oriented moderation platform for detecting harmful and adversarial
user-generated content. It is being built as an end-to-end software engineering and ML system:
from low-latency ingestion and algorithmic screening to transformer inference, vector retrieval,
human feedback, model evaluation, and reliability monitoring.

> **Current milestone:** synchronous and Kafka-backed asynchronous moderation, Redis idempotency,
> bounded retries, a dead-letter queue, a reproducible TF-IDF baseline, and an evaluated
> DistilBERT classifier.

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

### Asynchronous moderation

`POST /v1/moderation/jobs` accepts the same request with HTTP 202. It returns a stable `job_id`
and an `accepted` state. Poll `GET /v1/moderation/jobs/{job_id}` until the job is `succeeded` or
`failed`. Replaying the same `request_id` and content is idempotent; reusing the ID with different
content returns HTTP 409.

## Run locally

### Python

```bash
python -m venv .venv
```

Activate the environment, then run:

```bash
python -m pip install -e ".[dev,ml,transformer,distributed]"
uvicorn sentinel.main:app --app-dir src --reload
```

Open `http://localhost:8000/docs` for the interactive API documentation.

### Docker

```bash
docker compose up --build
```

This launches Kafka, Redis, the API, a worker, and topic initialization. Then submit a job in the
interactive documentation at `http://localhost:8000/docs`, or run:

```bash
python scripts/load_test_async.py --requests 100 --concurrency 10
```

### Local benchmark result

On a single-machine Docker Desktop deployment with 100 requests and 10 concurrent clients:

| Metric | Result |
| --- | ---: |
| Accepted / succeeded / failed | 100 / 100 / 0 |
| Incomplete at timeout | 0 |
| Submission throughput | 164.06 jobs/s |
| Terminal throughput | 94.62 jobs/s |
| Mean submission latency | 56.62 ms |
| p50 submission latency | 55.11 ms |
| p95 submission latency | 71.13 ms |

A controlled recovery test also confirmed that a job accepted while the worker was stopped remained
queued in Kafka and transitioned to `succeeded` after the worker restarted. These figures are local
portfolio evidence, not claims of production or global-scale performance.

See [`docs/distributed-architecture.md`](docs/distributed-architecture.md) for the component
design, at-least-once contract, failure behaviour, and benchmark interpretation.

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

## Train the transformer

Transformer fine-tuning is designed for a GPU environment. Open
`notebooks/sentinel_transformer_training_colab.ipynb` in Google Colab, select a GPU runtime,
and run the cells in order. The notebook clones this repository, recreates the dataset sample,
fine-tunes DistilBERT, compares it with the baseline, and downloads the resulting model and
metrics as a ZIP file.

Local installation is also available:

```bash
python -m pip install -e ".[dev,ml,transformer]"
python scripts/train_transformer.py --epochs 2 --batch-size 16
```

After placing the downloaded model folder at
`artifacts/models/transformer_toxicity`, restart the API. It will automatically load
`distilbert-toxicity-v1` instead of the TF-IDF model.

See [`docs/transformer-architecture.md`](docs/transformer-architecture.md) for the model design,
class-imbalance strategy, deployment interface, and limitations.

## Evaluation results

Both models use the same stratified 4,000-row test split from the 20,000-row Civil Comments
sample. Toxic-class metrics are emphasized because overall accuracy is misleading for the
imbalanced dataset.

| Metric | TF-IDF baseline | DistilBERT | Improvement |
| --- | ---: | ---: | ---: |
| Toxic precision | 0.464 | 0.609 | +0.145 |
| Toxic recall | 0.461 | 0.648 | +0.187 |
| Toxic F1 | 0.463 | 0.628 | +0.165 |
| ROC-AUC | 0.843 | 0.934 | +0.090 |
| Average precision | 0.474 | 0.695 | +0.222 |
| False positives | 165 | 129 | -36 |
| False negatives | 167 | 109 | -58 |

These results describe one held-out sample and are not production-safety claims. See the
[`DistilBERT model card`](docs/model-card-transformer.md) for intended use, evaluation scope,
risks, and limitations.

## Engineering roadmap

- **Milestone 1 — Foundation:** FastAPI, policy schemas, normalization, trie screening, tests,
  Docker and CI.
- **Milestone 2 — ML baseline:** Civil Comments streaming pipeline, TF-IDF logistic regression,
  model integration and binary toxicity evaluation.
- **Milestone 3 — Transformer:** fine-tune DistilBERT, compare it with the baseline, and load it
  through the existing model interface. **Complete.**
- **Milestone 4 — Distributed processing:** Kafka, consumer workers, idempotency, retries,
  dead-letter queues and a bounded load-test harness. **Complete.**
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
notebooks/             Reproducible Colab GPU training workflow
artifacts/metrics/     Versioned evaluation evidence
.github/workflows/     Continuous integration
```

## License

MIT
