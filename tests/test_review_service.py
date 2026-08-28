from datetime import UTC, datetime

import pytest

from sentinel.review.errors import ReviewAuthorizationError, ReviewConflictError
from sentinel.review.models import ReviewerRole, ReviewPrincipal, ReviewState
from sentinel.review.repository import InMemoryReviewRepository, JsonlReviewRepository
from sentinel.review.service import ReviewService
from sentinel.schemas.moderation import (
    Decision,
    ModerationResponse,
    ModerationSignal,
    SafetyCategory,
)


def response(request_id: str = "review-request-1") -> ModerationResponse:
    return ModerationResponse(
        request_id=request_id,
        decision=Decision.REVIEW,
        risk_score=0.65,
        signals=[
            ModerationSignal(
                source="heuristic",
                category=SafetyCategory.HARASSMENT,
                score=0.65,
                reason_code="targeted_abuse",
            )
        ],
        policy_version="test-policy-v1",
        evaluated_at=datetime.now(UTC),
    )


def principals() -> tuple[ReviewPrincipal, ReviewPrincipal, ReviewPrincipal]:
    return (
        ReviewPrincipal(reviewer_id="reviewer-1", role=ReviewerRole.REVIEWER),
        ReviewPrincipal(reviewer_id="senior-1", role=ReviewerRole.SENIOR_REVIEWER),
        ReviewPrincipal(reviewer_id="auditor-1", role=ReviewerRole.AUDITOR),
    )


def test_review_lifecycle_is_idempotent_and_hash_chained() -> None:
    service = ReviewService(InMemoryReviewRepository())
    reviewer, senior, auditor = principals()

    created = service.enqueue(response())
    duplicate = service.enqueue(response())
    assert created is not None
    assert duplicate is not None
    assert duplicate.case_id == created.case_id

    claimed = service.claim(created.case_id, reviewer)
    resolved = service.decide(created.case_id, reviewer, Decision.BLOCK, "confirmed_abuse")
    appealed = service.appeal(created.case_id, reviewer, "context_missing")
    appeal_claim = service.claim(created.case_id, senior)
    final = service.decide(created.case_id, senior, Decision.ALLOW, "appeal_upheld")
    events = service.audit(created.case_id, auditor)

    assert claimed.state == ReviewState.CLAIMED
    assert resolved.final_decision == Decision.BLOCK
    assert appealed.state == ReviewState.APPEALED
    assert appeal_claim.assigned_reviewer_id == "senior-1"
    assert final.final_decision == Decision.ALLOW
    assert [event.sequence for event in events] == [1, 2, 3, 4, 5, 6]
    assert all(events[index].previous_hash == events[index - 1].event_hash for index in range(1, 6))


def test_only_assigned_reviewer_can_decide() -> None:
    service = ReviewService(InMemoryReviewRepository())
    reviewer, senior, _auditor = principals()
    case = service.enqueue(response())
    assert case is not None
    service.claim(case.case_id, reviewer)

    with pytest.raises(ReviewAuthorizationError, match="different reviewer"):
        service.decide(case.case_id, senior, Decision.BLOCK, "confirmed_abuse")


def test_appeal_requires_senior_reviewer_for_claim_and_decision() -> None:
    service = ReviewService(InMemoryReviewRepository())
    reviewer, _senior, _auditor = principals()
    case = service.enqueue(response())
    assert case is not None
    service.claim(case.case_id, reviewer)
    service.decide(case.case_id, reviewer, Decision.BLOCK, "confirmed_abuse")
    service.appeal(case.case_id, reviewer, "context_missing")

    with pytest.raises(ReviewAuthorizationError, match="senior reviewer"):
        service.claim(case.case_id, reviewer)


def test_human_decision_cannot_remain_review() -> None:
    service = ReviewService(InMemoryReviewRepository())
    reviewer, _senior, _auditor = principals()
    case = service.enqueue(response())
    assert case is not None
    service.claim(case.case_id, reviewer)

    with pytest.raises(ReviewConflictError, match="allow or block"):
        service.decide(case.case_id, reviewer, Decision.REVIEW, "needs_more_review")


def test_feedback_export_is_auditor_only_and_contains_no_raw_content() -> None:
    service = ReviewService(InMemoryReviewRepository())
    reviewer, _senior, auditor = principals()
    case = service.enqueue(response())
    assert case is not None
    service.claim(case.case_id, reviewer)
    service.decide(case.case_id, reviewer, Decision.ALLOW, "context_safe")

    with pytest.raises(ReviewAuthorizationError, match="not authorized"):
        service.export_feedback(reviewer)
    export = service.export_feedback(auditor)
    serialized = export.model_dump_json()

    assert len(export.records) == 1
    assert export.records[0].human_decision == Decision.ALLOW
    assert '"text":' not in serialized
    assert '"image_base64":' not in serialized


def test_jsonl_repository_replays_append_only_projection(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    ledger = tmp_path / "review-ledger.jsonl"
    reviewer, _senior, auditor = principals()
    service = ReviewService(JsonlReviewRepository(ledger))
    case = service.enqueue(response())
    assert case is not None
    service.claim(case.case_id, reviewer)
    service.decide(case.case_id, reviewer, Decision.BLOCK, "confirmed_abuse")

    replayed = ReviewService(JsonlReviewRepository(ledger))
    restored = replayed.get(case.case_id, auditor)

    assert restored.state == ReviewState.RESOLVED
    assert restored.final_decision == Decision.BLOCK
    assert len(replayed.audit(case.case_id, auditor)) == 3


def test_jsonl_repository_rejects_tampered_audit_event(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    ledger = tmp_path / "review-ledger.jsonl"
    service = ReviewService(JsonlReviewRepository(ledger))
    case = service.enqueue(response())
    assert case is not None
    tampered = ledger.read_text(encoding="utf-8").replace(
        "automated_review_required",
        "silently_changed",
    )
    ledger.write_text(tampered, encoding="utf-8")

    with pytest.raises(ValueError, match="integrity failure"):
        JsonlReviewRepository(ledger)
