# Runbook: moderation latency SLO breach

## Trigger and impact

`SentinelFastPathLatencySLOBreach` fires when five-minute p95 latency for synchronous moderation
exceeds 250 ms for ten minutes. Users may experience timeouts even when availability remains high.

## Diagnose

1. Confirm the PromQL result in Grafana and compare throughput, in-flight requests, and decision
   mix over the same interval.
2. Inspect API logs and container resources.
3. Check Qdrant health and model-loading messages; distinguish dependency latency from CPU-bound
   inference.

```bash
docker compose ps
docker compose logs --tail 200 api qdrant
docker stats --no-stream
```

## Mitigate

- If Qdrant is degraded, preserve its logs and use the engine's existing graceful vector fallback.
- If inference is saturated, reduce nonessential load or add API capacity in an orchestrated
  deployment.
- Roll back the most recent model or application release if the breach began with that release.

## Verify and close

Run a bounded test, confirm p95 remains below 250 ms for at least ten minutes, and verify that
availability and safety decisions did not regress. Attach the before/after dashboard interval to
the incident record.
