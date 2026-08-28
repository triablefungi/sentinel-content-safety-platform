# Human Review and Feedback Architecture

## Workflow

Sentinel creates a review case when automation returns `review` or when text and image modalities
disagree. A reviewer claims the case and records an `allow` or `block` decision with a bounded
reason code. A resolved case may be appealed, but only a senior reviewer can claim and decide the
appeal. Auditors can inspect the event history and export privacy-conscious feedback records.

## Privacy boundary

The review ledger deliberately excludes raw text, Base64 images, filenames, URLs, model tensors,
and free-form reviewer notes. It stores opaque request and case identifiers, automated scores,
categories, model/policy versions, state transitions, bounded reason codes, and timestamps. A real
review interface would resolve the request identifier through a separate access-controlled content
system with retention, redaction, and regional policy enforcement.

## Authorization

Bearer tokens are compared against SHA-256 hashes with constant-time comparison. Roles are:

| Role | Permissions |
| --- | --- |
| Reviewer | List, inspect, claim, decide, and submit appeals |
| Senior reviewer | Reviewer permissions plus appeal claim and decision |
| Auditor | Read cases and audit histories; export resolved feedback |

The tracked authorization file contains development-only token hashes. Production secrets must be
random, rotated, delivered through a secrets manager, and paired with an identity provider and
short-lived credentials. Authentication failures return 401; valid identities without permission
receive 403.

## Audit integrity and persistence

Every state transition appends a JSONL record containing the current case projection and an audit
event. Events include a monotonically increasing sequence, the previous event hash, and a SHA-256
digest of canonical event fields. Startup replays the ledger and rejects broken hashes, sequences,
or links. A process-level lock prevents concurrent claims in the local single-process deployment.

For horizontal production deployment, replace the file repository with a transactional database
or event log providing compare-and-set transitions, encryption, backups, retention enforcement,
and cross-instance concurrency control.

## Feedback export

Only resolved cases enter the export. Records contain model and human decisions, risk score,
categories, policy version, reason code, resolution time, and whether an appeal occurred. They do
not contain user content. The export is suitable for aggregate error analysis and sampling; model
retraining still requires separately approved, access-controlled content joins and dataset review.

## Operations

Prometheus exposes low-cardinality action outcomes, backlog by state, and resolution time. Grafana
shows backlog and action rates. The local alert fires when pending plus appealed cases exceed 100
for 15 minutes; see the [review-backlog runbook](runbooks/review-backlog.md).
