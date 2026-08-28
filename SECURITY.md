# Security Policy

## Supported version

The `main` branch is the supported portfolio release. This repository is a reference
implementation and is not operated as a public moderation service.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is available for this repository. Do not open
a public issue containing exploit details, credentials, user content, model artifacts, or audit
records. Include the affected component, reproducible steps using sanitized data, impact, and a
suggested mitigation if known.

## Security boundaries

- Local demonstration tokens are public examples and must never be reused in another environment.
- Raw user text, image bytes, and reviewer notes must not enter metrics, audit events, or feedback
  exports.
- Model artifacts are downloaded separately, checksum-verified where supported, and excluded from
  Git.
- Production deployments require TLS termination, managed secrets, authenticated data services,
  network isolation, centralized rate limiting, and a transactional review store.

See [`docs/threat-model.md`](docs/threat-model.md) for threats, implemented controls, and residual
risks.
