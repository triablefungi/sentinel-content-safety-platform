# Multimodal Safety Architecture

## Scope

Sentinel adds an optional synchronous image-safety path without changing the existing text or
Kafka-backed APIs. `POST /v1/moderate/multimodal` accepts one bounded Base64 image, its declared
media type, optional text, and an optional request ID. Asynchronous image transport is deliberately
out of scope until object-storage references, malware scanning, retention, and deletion semantics
are defined; image bytes are not placed directly on Kafka.

## Trust boundary

The API treats the filename, media-type claim, metadata, and encoded bytes as untrusted. The image
boundary:

1. rejects malformed Base64 and payloads over 5 MiB;
2. identifies JPEG, PNG, or WebP from its binary signature;
3. verifies that the signature matches the declared media type;
4. extracts dimensions before decompression and enforces 8,192 pixels per side and 20 megapixels;
5. rejects animation flags; and
6. performs a full Pillow decode, decompression-bomb check, EXIF orientation, RGB conversion, and
   metadata-free pixel copy inside the optional model adapter.

The API returns format, dimensions, and received-byte count, but never returns, persists, or logs
the Base64 payload. Production deployments still require request-size limits at the reverse proxy,
authentication, rate limiting, malware scanning, retention controls, and isolated inference.

## Model boundary

`ImageSafetyModel` returns model scores for reviewed `sexual_content` and
`graphic_violence` categories. The local timm adapter refuses to load without
`sentinel_image_metadata.json`. That file maps exact checkpoint labels to Sentinel categories;
unknown labels are never guessed from their wording.

The repository does not silently download a model at application startup. The explicit
`scripts/download_image_model.py` command retrieves the pinned
`OwenElliott/image-safety-classifier-m` candidate and accepts it only when its safetensors SHA-256
matches the reviewed value. Startup repeats the checksum verification before loading the local
artifact. The adapter constructs a known `timm` SwiftFormer architecture locally and does not
execute model-repository code.

The reviewed mapping is `NSFW` to `sexual_content` and `NSFL` to `graphic_violence`; `SFW` is not
mapped to a safety category. The checkpoint is MIT licensed and compact, but its approximately
320,000-image training corpus is proprietary and web-scraped, and the model author reports that
the NSFL class is underrepresented. These provenance and slice-coverage limits prevent automatic
promotion. A versioned, independently reviewed evaluation set and per-category gates are required
before any production claim.

## Fusion policy

Text and image evidence retain their source, category, score, and reason code. The strictest risk
wins: scores from 0.40 route to review and scores from 0.85 block. When one modality intervenes and
the other allows, Sentinel adds a `cross_modal_disagreement` signal without weakening the stricter
decision. This makes disagreement measurable for later calibration and human-review analysis.

## Failure behaviour

- No configured image model: HTTP 503; text-only moderation remains available.
- Invalid Base64 or corrupt supported image: HTTP 422.
- Signature/type mismatch or unsupported/animated format: HTTP 415.
- Encoded, dimensional, or decoded-pixel limit breach: HTTP 413.
- Invalid model score or category: fail the request rather than emitting an untrusted decision.

## Limitations

- Image safety is highly context-dependent and culturally sensitive.
- The initial endpoint handles one still image and optional English text.
- OCR, memes, video, audio, multi-image context, and cross-frame reasoning are not implemented.
- The synthetic API tests validate policy and security boundaries, not real model quality.
- The current checkpoint is a candidate; it must not be promoted until an independently reviewed
  image evaluation suite passes per-category recall, false-positive, and robustness gates.
