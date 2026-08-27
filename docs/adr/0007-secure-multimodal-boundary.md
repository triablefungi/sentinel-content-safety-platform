# ADR 0007: Keep image ingestion bounded and model loading explicit

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Adding image classification introduces decompression bombs, content-type confusion, animation,
metadata leakage, large-message transport, model-provenance, and label-mapping risks that do not
exist in the text endpoint.

## Decision

Provide a separate synchronous JSON endpoint with a 5 MiB encoded-image boundary. Verify supported
formats from bytes, enforce dimension and pixel limits before full decoding, reject animation, and
perform sanitized decoding only inside the optional local vision adapter. Do not send raw images
through Kafka or persist them.

Require a local model directory and a reviewed `sentinel_image_metadata.json` mapping exact model
labels to Sentinel policy categories. If the artifact is absent, return HTTP 503 rather than using a
placeholder classifier or downloading a checkpoint during startup.

Fuse modality scores with a strictest-signal policy and record disagreement without reducing a
block to an allow or review.

## Consequences

Text-only deployments remain lightweight and deterministic, and image-model provenance is visible.
The Base64 API is simple for a bounded portfolio demonstration but has overhead; a production
asynchronous design should upload to quarantined object storage and queue only an immutable object
reference. Model evaluation, OCR, multilingual text in images, and abuse-specific red teaming remain
required before promotion.
