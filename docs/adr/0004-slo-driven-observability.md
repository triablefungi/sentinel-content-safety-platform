# ADR 0004: SLO-driven, low-cardinality observability

- **Status:** Accepted
- **Date:** 2026-08-24

## Context

Sentinel needs evidence for availability, latency, throughput, and asynchronous processing without
creating an expensive or privacy-sensitive telemetry system. User text, request IDs, job IDs, and
exception messages are unbounded and must not become metric labels.

## Decision

Expose Prometheus metrics from the API and worker using fixed labels such as templated route,
method, status code, decision, processing path, state, and bounded error code. Use separate custom
registries for each process. Provision Prometheus alerts, a Grafana dashboard, readiness checks,
and operational runbooks in Compose. Return request correlation IDs in headers but exclude them
from metrics.

## Consequences

The local stack is reproducible and each SLO has a query and response procedure. Cardinality remains
bounded and raw content is absent from telemetry. Metrics are process-local; production deployment
would require durable long-term storage, authentication, trace propagation, and aggregation across
replicas. OpenTelemetry traces remain a future increment rather than a prerequisite for honest SLO
instrumentation.
