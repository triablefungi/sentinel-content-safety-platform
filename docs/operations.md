# Local operations guide

## Start the stack

```bash
docker compose up -d --build
docker compose ps
```

| Component | URL | Purpose |
| --- | --- | --- |
| API | `http://localhost:8000/docs` | Submit synchronous and asynchronous moderation requests |
| Prometheus | `http://localhost:9090` | Query SLIs and inspect alerts |
| Grafana | `http://localhost:3000` | View the provisioned Sentinel operations dashboard |
| Qdrant | `http://localhost:6333/dashboard` | Inspect local vector collections |

Grafana permits anonymous Viewer access in this local-only Compose configuration. Do not use that
setting for an internet-accessible deployment.

## Verify telemetry

```bash
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
curl http://localhost:9090/-/ready
```

The API also returns an `X-Request-ID` header. A caller may supply a safe `X-Request-ID`; otherwise
Sentinel creates one. This identifier is intended for log and trace correlation and must never be
used as a Prometheus label.

Verify the development human-review workflow with:

```bash
python scripts/verify_review_workflow.py
```

The verifier exercises claim, decision, appeal, senior review, audit history, and feedback export.
The bundled bearer tokens are local demonstrations only. Review backlog and actions appear on the
Grafana dashboard, and the backlog alert routes to `docs/runbooks/review-backlog.md`.

Generate representative traffic with:

```bash
python scripts/load_test_async.py --requests 100 --concurrency 10
```

Then open the **Sentinel / Operations and SLOs** dashboard in Grafana. The dashboard shows
availability, p95 latency, throughput, moderation decisions, worker outcomes, retries, and DLQ
events.

## Stop the stack

```bash
docker compose down
```

Named volumes retain Redis, Qdrant, the append-only review ledger, Prometheus, and Grafana data.
Add `--volumes` only when an intentional destructive reset is required.
