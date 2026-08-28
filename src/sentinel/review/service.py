import threading
from datetime import UTC, datetime
from functools import wraps
from uuid import NAMESPACE_URL, uuid4, uuid5

from sentinel.review.errors import (
    ReviewAuthorizationError,
    ReviewConflictError,
    ReviewNotFoundError,
)
from sentinel.review.models import (
    FeedbackExport,
    FeedbackRecord,
    ReviewAction,
    ReviewAuditEvent,
    ReviewCase,
    ReviewerRole,
    ReviewPrincipal,
    ReviewState,
    audit_event_digest,
)
from sentinel.review.repository import ReviewRepository
from sentinel.schemas.moderation import (
    Decision,
    ModerationResponse,
    SafetyCategory,
)

_REVIEW_ROLES = {ReviewerRole.REVIEWER, ReviewerRole.SENIOR_REVIEWER}
_READ_ROLES = {*_REVIEW_ROLES, ReviewerRole.AUDITOR}


def _synchronized(method):  # type: ignore[no-untyped-def]
    @wraps(method)
    def wrapper(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class ReviewService:
    def __init__(self, repository: ReviewRepository) -> None:
        self._repository = repository
        self._lock = threading.RLock()

    @_synchronized
    def enqueue(self, response: ModerationResponse) -> ReviewCase | None:
        categories = sorted({signal.category for signal in response.signals}, key=str)
        requires_review = response.decision == Decision.REVIEW or (
            SafetyCategory.CROSS_MODAL_DISAGREEMENT in categories
        )
        if not requires_review:
            return None
        existing = self._repository.find_by_request_id(response.request_id)
        if existing is not None:
            return existing
        case_id = str(
            uuid5(
                NAMESPACE_URL,
                f"sentinel-review:{response.request_id}:{response.policy_version}",
            )
        )
        case = ReviewCase(
            case_id=case_id,
            request_id=response.request_id,
            automated_decision=response.decision,
            automated_risk_score=response.risk_score,
            signal_categories=categories,
            policy_version=response.policy_version,
        )
        event = self._event(
            case=case,
            action=ReviewAction.CREATED,
            actor_id="system",
            actor_role=None,
            from_state=None,
            reason_code="automated_review_required",
        )
        self._repository.commit(case, event)
        return case

    def list_cases(
        self,
        principal: ReviewPrincipal,
        state: ReviewState | None = None,
    ) -> list[ReviewCase]:
        self._require(principal, _READ_ROLES)
        return self._repository.list_cases(state)

    def backlog(self) -> dict[ReviewState, int]:
        return {state: len(self._repository.list_cases(state)) for state in ReviewState}

    def get(self, case_id: str, principal: ReviewPrincipal) -> ReviewCase:
        self._require(principal, _READ_ROLES)
        return self._get(case_id)

    @_synchronized
    def claim(self, case_id: str, principal: ReviewPrincipal) -> ReviewCase:
        self._require(principal, _REVIEW_ROLES)
        case = self._get(case_id)
        if case.state == ReviewState.APPEALED and principal.role != ReviewerRole.SENIOR_REVIEWER:
            raise ReviewAuthorizationError("only a senior reviewer can claim an appeal")
        if case.state not in {ReviewState.PENDING, ReviewState.APPEALED}:
            raise ReviewConflictError(f"case cannot be claimed from state {case.state}")
        previous_state = case.state
        case.state = ReviewState.CLAIMED
        case.assigned_reviewer_id = principal.reviewer_id
        case.updated_at = datetime.now(UTC)
        event = self._event(
            case=case,
            action=ReviewAction.CLAIMED,
            actor_id=principal.reviewer_id,
            actor_role=principal.role,
            from_state=previous_state,
            reason_code="reviewer_claimed",
        )
        self._repository.commit(case, event)
        return case

    @_synchronized
    def decide(
        self,
        case_id: str,
        principal: ReviewPrincipal,
        decision: Decision,
        reason_code: str,
    ) -> ReviewCase:
        self._require(principal, _REVIEW_ROLES)
        if decision == Decision.REVIEW:
            raise ReviewConflictError("a human decision must be allow or block")
        case = self._get(case_id)
        if case.state != ReviewState.CLAIMED:
            raise ReviewConflictError(f"case cannot be decided from state {case.state}")
        if case.assigned_reviewer_id != principal.reviewer_id:
            raise ReviewAuthorizationError("case is assigned to a different reviewer")
        events = self._repository.audit(case_id)
        is_appeal = any(event.action == ReviewAction.APPEALED for event in events)
        if is_appeal and principal.role != ReviewerRole.SENIOR_REVIEWER:
            raise ReviewAuthorizationError("only a senior reviewer can decide an appeal")
        now = datetime.now(UTC)
        case.state = ReviewState.RESOLVED
        case.final_decision = decision
        case.decision_reason_code = reason_code
        case.updated_at = now
        case.resolved_at = now
        event = self._event(
            case=case,
            action=ReviewAction.APPEAL_DECIDED if is_appeal else ReviewAction.DECIDED,
            actor_id=principal.reviewer_id,
            actor_role=principal.role,
            from_state=ReviewState.CLAIMED,
            reason_code=reason_code,
        )
        self._repository.commit(case, event)
        return case

    @_synchronized
    def appeal(
        self,
        case_id: str,
        principal: ReviewPrincipal,
        reason_code: str,
    ) -> ReviewCase:
        self._require(principal, _REVIEW_ROLES)
        case = self._get(case_id)
        if case.state != ReviewState.RESOLVED:
            raise ReviewConflictError(f"case cannot be appealed from state {case.state}")
        case.state = ReviewState.APPEALED
        case.assigned_reviewer_id = None
        case.appeal_reason_code = reason_code
        case.updated_at = datetime.now(UTC)
        event = self._event(
            case=case,
            action=ReviewAction.APPEALED,
            actor_id=principal.reviewer_id,
            actor_role=principal.role,
            from_state=ReviewState.RESOLVED,
            reason_code=reason_code,
        )
        self._repository.commit(case, event)
        return case

    def audit(self, case_id: str, principal: ReviewPrincipal) -> list[ReviewAuditEvent]:
        self._require(principal, _READ_ROLES)
        self._get(case_id)
        return self._repository.audit(case_id)

    def export_feedback(self, principal: ReviewPrincipal) -> FeedbackExport:
        self._require(principal, {ReviewerRole.AUDITOR})
        records = []
        for case in self._repository.list_cases(ReviewState.RESOLVED):
            if case.final_decision is None or case.decision_reason_code is None:
                continue
            if case.resolved_at is None:
                continue
            events = self._repository.audit(case.case_id)
            records.append(
                FeedbackRecord(
                    case_id=case.case_id,
                    request_id=case.request_id,
                    automated_decision=case.automated_decision,
                    automated_risk_score=case.automated_risk_score,
                    signal_categories=case.signal_categories,
                    policy_version=case.policy_version,
                    human_decision=case.final_decision,
                    decision_reason_code=case.decision_reason_code,
                    resolved_at=case.resolved_at,
                    appealed=any(event.action == ReviewAction.APPEALED for event in events),
                )
            )
        return FeedbackExport(records=records)

    def _get(self, case_id: str) -> ReviewCase:
        case = self._repository.get(case_id)
        if case is None:
            raise ReviewNotFoundError("review case not found")
        return case

    @staticmethod
    def _require(principal: ReviewPrincipal, roles: set[ReviewerRole]) -> None:
        if principal.role not in roles:
            raise ReviewAuthorizationError("reviewer role is not authorized")

    def _event(
        self,
        *,
        case: ReviewCase,
        action: ReviewAction,
        actor_id: str,
        actor_role: ReviewerRole | None,
        from_state: ReviewState | None,
        reason_code: str,
    ) -> ReviewAuditEvent:
        existing = self._repository.audit(case.case_id)
        previous_hash = existing[-1].event_hash if existing else "0" * 64
        occurred_at = datetime.now(UTC)
        event_id = str(uuid4())
        payload = {
            "event_id": event_id,
            "case_id": case.case_id,
            "sequence": len(existing) + 1,
            "action": action.value,
            "actor_id": actor_id,
            "actor_role": actor_role.value if actor_role else None,
            "from_state": from_state.value if from_state else None,
            "to_state": case.state.value,
            "reason_code": reason_code,
            "occurred_at": occurred_at.isoformat(),
            "previous_hash": previous_hash,
        }
        event_hash = audit_event_digest(payload)
        return ReviewAuditEvent(**payload, event_hash=event_hash)
