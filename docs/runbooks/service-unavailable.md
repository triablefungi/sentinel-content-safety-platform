# Runbook: Sentinel target unavailable

## Trigger and impact

`SentinelTargetDown` fires when Prometheus cannot scrape the API or worker for two minutes. API
failure prevents new requests; worker failure leaves accepted jobs buffered in Kafka.

## Diagnose

```bash
docker compose ps -a
docker compose logs --tail 200 api worker kafka redis qdrant
```

Verify API readiness and inspect Prometheus targets:

```bash
curl http://localhost:8000/health/ready
```

Open `http://localhost:9090/targets`. Preserve the first error, container exit code, and relevant
logs before changing state.

## Mitigate

Restart only the failed stateless service first:

```bash
docker compose restart api
docker compose restart worker
```

If a dependency is unhealthy, restart that dependency and then the affected consumer. Do not
delete volumes during incident response.

## Verify and close

- `docker compose ps` reports the API and dependencies healthy and the worker running.
- `/health/ready` returns HTTP 200.
- Prometheus targets return to `UP` and the alert resolves.
- Submit one asynchronous job and verify it reaches a terminal state.

Record detection time, user impact, root cause, recovery action, and a follow-up owner.
