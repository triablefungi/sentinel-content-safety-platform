# ADR 0008: Use a pinned SwiftFormer image-safety candidate

- Status: accepted for evaluation, not approved for production
- Date: 2026-08-27

## Context

The multimodal boundary needs a real, locally runnable checkpoint to validate end-to-end image
moderation. The candidate must cover both sexual content and graphic violence, run reasonably on
CPU, expose explicit labels, avoid runtime network access, and have redistributable model weights.

## Decision

Use `OwenElliott/image-safety-classifier-m` at pinned revision `a5ce9ee` as the Milestone 8
evaluation candidate. It is a compact SwiftFormer classifier with `NSFL`, `NSFW`, and `SFW`
labels. Sentinel maps `NSFL` to `graphic_violence`, `NSFW` to `sexual_content`, and does not map
`SFW` to a safety category.

Acquisition is explicit. A separate script downloads only `model.safetensors`, verifies its
reviewed SHA-256, and writes local metadata. Application startup repeats the checksum check,
constructs the known timm architecture locally, and never executes repository-supplied code.

## Consequences

- One compact model covers the two initial image-policy categories.
- Safetensors and checksum verification reduce model supply-chain risk.
- The model remains outside Git and Docker build context unless deliberately mounted.
- The proprietary, web-scraped training set limits independent provenance review.
- The author reports an underrepresented NSFL slice, so aggregate accuracy cannot justify
  production use.
- Promotion requires a versioned evaluation corpus, per-category recall and false-positive gates,
  adversarial transformations, and documented threshold review.
