# Human-review backlog runbook

## Trigger

`SentinelReviewBacklogHigh` fires when pending and appealed cases remain above 100 for 15 minutes.
This is a local demonstration threshold, not a validated production staffing target.

## Triage

1. Confirm the backlog by state with `sentinel_review_backlog`.
2. Check `sentinel_review_events_total` for failed claims or decisions.
3. Compare moderation decision volume with review creation rate.
4. Verify that the API can append to the review ledger and that its volume has free space.
5. Inspect whether one policy version or signal category caused the increase.

Do not copy raw user content into incident tickets, metric labels, or chat channels. Use case and
request identifiers to access governed source systems.

## Mitigation

- Restore ledger access or reviewer authentication failures first.
- Reassign available trained reviewers according to category and locale expertise.
- Prioritize appeals, imminent-SLA cases, severe-risk cases, and cross-modal disagreements.
- Do not silently raise automated thresholds to reduce queue depth.

## Recovery

The alert may close after the pending and appealed total remains at or below 100. Confirm that
resolution latency is returning to its operating range and record the affected policy versions,
categories, duration, and corrective action.
