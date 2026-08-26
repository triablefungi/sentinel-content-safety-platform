# Service-level objectives

Sentinel uses service-level indicators (SLIs) that can be computed from Prometheus metrics. These
targets are engineering objectives for a documented environment, not claims that this portfolio
deployment has operated at global scale.

## Objectives

| User journey | SLI | Objective | Window |
| --- | --- | ---: | --- |
| API requests | Non-5xx responses / eligible responses | 99.9% | Rolling 30 days |
| Synchronous moderation | p95 request duration for `POST /v1/moderate/text` | < 250 ms | Rolling 5 minutes |
| Accepted asynchronous jobs | Jobs reaching `succeeded`, `failed`, or the DLQ | 99.99% | Within 10 minutes |
| Model promotion | Category-specific safety metrics do not regress below the approved threshold | 100% of releases | Per release |

At 99.9% availability, a 30-day month permits approximately 43 minutes and 50 seconds of error
budget. Health probes and the Prometheus endpoint are excluded from the user-journey availability
calculation.

## PromQL

Availability:

```promql
1 - (
  sum(rate(sentinel_http_requests_total{route=~"/v1/.*",status_code=~"5.."}[5m]))
  /
  clamp_min(sum(rate(sentinel_http_requests_total{route=~"/v1/.*"}[5m])), 0.001)
)
```

Synchronous p95 latency:

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(sentinel_http_request_duration_seconds_bucket{
      route="/v1/moderate/text",method="POST"
    }[5m])
  )
)
```

Worker retries and dead-letter events:

```promql
sum(rate(sentinel_worker_events_total{outcome="retry_scheduled"}[5m]))
sum(increase(sentinel_worker_events_total{outcome="dlq"}[10m]))
```

The asynchronous objective ultimately requires an end-to-end age or backlog histogram in a
durable production deployment. The current terminal, retry, and DLQ counters are sufficient for
local failure exercises and alerting, but are not a substitute for long-window production data.

## Alert policy

Prometheus loads `ops/prometheus/alerts.yml`. Alerts cover scrape failures, availability error
budget burn, fast-path latency, elevated retry rates, and any DLQ event. Each alert links to a
runbook. During an incident, preserve logs and the triggering query before restarting services.
