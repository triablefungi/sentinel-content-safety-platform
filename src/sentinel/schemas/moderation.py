from datetime import UTC, datetime
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
    COORDINATED_ABUSE = "coordinated_abuse"
    SEXUAL_CONTENT = "sexual_content"
    GRAPHIC_VIOLENCE = "graphic_violence"
    CROSS_MODAL_DISAGREEMENT = "cross_modal_disagreement"


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


class ImageMediaType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"


class MultimodalModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    image_base64: str = Field(min_length=1, max_length=7_000_000)
    media_type: ImageMediaType
    text: str | None = Field(default=None, max_length=5_000)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("text")
    @classmethod
    def reject_blank_optional_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class ImageMetadata(BaseModel):
    format: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    bytes_received: int = Field(gt=0)


class MultimodalModerationResponse(ModerationResponse):
    modalities: list[str]
    image: ImageMetadata


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class JobState(StrEnum):
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ModerationJob(BaseModel):
    job_id: str
    request_id: str
    state: JobState
    attempt: int = Field(default=0, ge=0)
    result: ModerationResponse | None = None
    error_code: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StoredModerationJob(BaseModel):
    job: ModerationJob
    request_fingerprint: str


class ModerationJobEvent(BaseModel):
    job_id: str
    request: ModerationRequest
    attempt: int = Field(default=0, ge=0)
