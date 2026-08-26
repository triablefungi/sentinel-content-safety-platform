import asyncio

from fastapi import APIRouter, HTTPException, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST

from sentinel.core.engine import ModerationEngine
from sentinel.distributed.errors import IdempotencyConflictError, QueueUnavailableError
from sentinel.distributed.protocols import JobService
from sentinel.observability.metrics import SentinelMetrics
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


@router.get("/health/ready", tags=["operations"])
async def readiness(request: Request) -> dict[str, str]:
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="service is not ready",
        )
    return {"status": "ready"}


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    telemetry: SentinelMetrics = request.app.state.metrics
    return Response(
        content=telemetry.render(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.post(
    "/v1/moderate/text",
    response_model=ModerationResponse,
    status_code=status.HTTP_200_OK,
    tags=["moderation"],
)
async def moderate_text(payload: ModerationRequest, request: Request) -> ModerationResponse:
    engine: ModerationEngine = request.app.state.moderation_engine
    telemetry: SentinelMetrics = request.app.state.metrics
    started = telemetry.timer()
    response = engine.moderate(payload)
    telemetry.moderation_duration.labels("synchronous").observe(
        telemetry.timer() - started
    )
    telemetry.record_decision(response.decision.value, "synchronous")
    return response


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
    telemetry: SentinelMetrics = request.app.state.metrics
    if service is None:
        telemetry.record_submission("disabled")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="distributed moderation is not enabled",
        )
    try:
        job = await asyncio.to_thread(service.submit, payload)
        telemetry.record_submission("accepted")
        return job
    except IdempotencyConflictError as exc:
        telemetry.record_submission("idempotency_conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id was already used with different content",
        ) from exc
    except QueueUnavailableError as exc:
        telemetry.record_submission("queue_unavailable")
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
