from fastapi import APIRouter, Request, status

from sentinel.core.engine import ModerationEngine
from sentinel.schemas.moderation import HealthResponse, ModerationRequest, ModerationResponse

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

