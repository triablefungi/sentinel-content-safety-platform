import asyncio

from fastapi import APIRouter, HTTPException, Request, status

from sentinel.core.engine import ModerationEngine
from sentinel.distributed.errors import IdempotencyConflictError, QueueUnavailableError
from sentinel.distributed.protocols import JobService
from sentinel.schemas.moderation import (
    HealthResponse,
    ModerationJob,
    ModerationRequest,
    ModerationResponse,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["operations"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="sentinel-api", version="0.1.0")


@router.post(
    "/v1/moderate/text",
    response_model=ModerationResponse,
    status_code=status.HTTP_200_OK,
    tags=["moderation"],
)
async def moderate_text(payload: ModerationRequest, request: Request) -> ModerationResponse:
    engine: ModerationEngine = request.app.state.moderation_engine
    return engine.moderate(payload)


@router.post(
    "/v1/moderation/jobs",
    response_model=ModerationJob,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["distributed moderation"],
)
async def submit_moderation_job(
    payload: ModerationRequest,
    request: Request,
) -> ModerationJob:
    service: JobService | None = request.app.state.job_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="distributed moderation is not enabled",
        )
    try:
        return await asyncio.to_thread(service.submit, payload)
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id was already used with different content",
        ) from exc
    except QueueUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="moderation queue is unavailable",
        ) from exc


@router.get(
    "/v1/moderation/jobs/{job_id}",
    response_model=ModerationJob,
    tags=["distributed moderation"],
)
async def get_moderation_job(job_id: str, request: Request) -> ModerationJob:
    service: JobService | None = request.app.state.job_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="distributed moderation is not enabled",
        )
    job = await asyncio.to_thread(service.get, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job
