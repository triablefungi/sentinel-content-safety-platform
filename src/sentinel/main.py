import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sentinel.api.routes import router
from sentinel.distributed.protocols import JobService
from sentinel.runtime import build_moderation_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    job_service: JobService | None = None
    moderation_engine = build_moderation_engine()
    app.state.moderation_engine = moderation_engine
    if os.getenv("SENTINEL_DISTRIBUTED_ENABLED", "false").lower() in {"1", "true", "yes"}:
        from sentinel.distributed.bootstrap import build_job_service_from_env

        job_service = build_job_service_from_env()
    app.state.job_service = job_service
    try:
        yield
    finally:
        if job_service is not None:
            job_service.close()
        moderation_engine.close()


app = FastAPI(
    title="Sentinel Content Safety API",
    description="Layered moderation for user-generated content.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
