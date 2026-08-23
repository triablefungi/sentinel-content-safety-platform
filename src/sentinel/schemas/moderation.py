from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Decision(StrEnum):
    ALLOW = "allow"
    REVIEW = "review"
    BLOCK = "block"


class SafetyCategory(StrEnum):
    HARASSMENT = "harassment"
    IDENTITY_ATTACK = "identity_attack"
    THREAT = "threat"
    TOXICITY = "toxicity"


class ModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=5_000)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class ModerationSignal(BaseModel):
    source: str
    category: SafetyCategory
    score: float = Field(ge=0.0, le=1.0)
    reason_code: str


class ModerationResponse(BaseModel):
    request_id: str
    decision: Decision
    risk_score: float = Field(ge=0.0, le=1.0)
    signals: list[ModerationSignal]
    policy_version: str
    evaluated_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
