# ADR 0010: Defense-in-depth release boundary

## Status

Accepted

## Context

Sentinel accepts adversarial user-controlled text and image payloads, loads high-value model
artifacts, and exposes reviewer actions. Model quality alone cannot protect this boundary. The API,
container, configuration, dependency graph, and operator workflow all require independent controls.

## Decision

Use layered, configurable controls:

1. Bound request bodies before schema decoding.
2. Apply an in-process token-bucket limiter for the single-instance demonstration and require rate
   limiting in production configuration.
3. Emit restrictive HTTP security and cache headers, with HSTS required only for TLS deployments.
4. Reject unsafe production configuration during application initialization.
5. Run the container as a non-root user with a read-only root filesystem, dropped capabilities,
   and no privilege escalation.
6. Bind local operational ports to loopback.
7. Generate a deterministic CycloneDX SBOM from the lockfile and enforce it in CI.
8. Use CodeQL and Dependabot for static analysis and dependency-update visibility.

## Consequences

The local environment has a materially smaller attack surface and produces reviewable release
evidence. The in-process limiter is deliberately not represented as a distributed production
control: multiple replicas require a gateway or shared rate-limit service. Compose remains a local
demonstration, not an internet-facing deployment manifest.
