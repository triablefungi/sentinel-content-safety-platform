import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from sentinel.schemas.moderation import Decision, SafetyCategory


def audit_event_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()


class ReviewState(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RESOLVED = "resolved"
    APPEALED = "appealed"


class ReviewerRole(StrEnum):
    REVIEWER = "reviewer"
    SENIOR_REVIEWER = "senior_reviewer"
    AUDITOR = "auditor"


class ReviewAction(StrEnum):
    CREATED = "created"
    CLAIMED = "claimed"
    DECIDED = "decided"
    APPEALED = "appealed"
    APPEAL_DECIDED = "appeal_decided"


class ReviewPrincipal(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=128)
    role: ReviewerRole


class ReviewCase(BaseModel):
    case_id: str
    request_id: str
    automated_decision: Decision
    automated_risk_score: float = Field(ge=0.0, le=1.0)
    signal_categories: list[SafetyCategory]
    policy_version: str
    state: ReviewState = ReviewState.PENDING
    assigned_reviewer_id: str | None = None
    final_decision: Decision | None = None
    decision_reason_code: str | None = None
    appeal_reason_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Decision
    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")


class ReviewAppealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason_code: str = Field(pattern=r"^[a-z][a-z0-9_]{2,63}$")


class ReviewAuditEvent(BaseModel):
    event_id: str
    case_id: str
    sequence: int = Field(ge=1)
    action: ReviewAction
    actor_id: str
    actor_role: ReviewerRole | None = None
    from_state: ReviewState | None = None
    to_state: ReviewState
    reason_code: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    previous_hash: str
    event_hash: str


class FeedbackRecord(BaseModel):
    case_id: str
    request_id: str
    automated_decision: Decision
    automated_risk_score: float
    signal_categories: list[SafetyCategory]
    policy_version: str
    human_decision: Decision
    decision_reason_code: str
    resolved_at: datetime
    appealed: bool


class FeedbackExport(BaseModel):
    schema_version: str = "sentinel-review-feedback-v1"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    records: list[FeedbackRecord]
