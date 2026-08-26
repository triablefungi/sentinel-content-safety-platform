# Runbook: asynchronous job pipeline degradation

## Trigger and impact

`SentinelRetryRateHigh` or `SentinelDLQEventDetected` indicates processing failures. Kafka preserves
accepted work while a worker is unavailable, but users wait longer for a decision.

## Diagnose

```bash
docker compose ps -a
docker compose logs --tail 250 worker kafka redis
```

Check worker outcome metrics and preserve the error code associated with terminal failures. Verify
Kafka and Redis are healthy before restarting the worker.

## Mitigate

```bash
docker compose restart worker
```

If a deterministic payload or model version causes repeated failure, stop the worker, roll back the
offending release, and then resume consumption. Do not blindly replay the DLQ; correct or quarantine
the cause first.

## Verify and close

- A new job transitions from `accepted` to `succeeded` or an explained `failed` state.
- Retry rate returns to baseline and no new DLQ events occur for ten minutes.
- Buffered jobs drain without duplicate decisions; the idempotency conflict behaviour remains 409.
- Document whether capacity, dependency failure, data quality, or application code caused the event.
