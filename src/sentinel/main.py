import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from sentinel.api.routes import router
from sentinel.core.engine import ModerationEngine
from sentinel.ml.baseline import SklearnToxicityModel


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    model_path = Path(
        os.getenv("SENTINEL_MODEL_PATH", "artifacts/models/toxicity_baseline.joblib")
    )
    toxicity_model = SklearnToxicityModel.load(model_path) if model_path.exists() else None
    app.state.moderation_engine = ModerationEngine.default(toxicity_model=toxicity_model)
    yield


app = FastAPI(
    title="Sentinel Content Safety API",
    description="Layered moderation for user-generated content.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
