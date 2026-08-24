import os
from pathlib import Path

from sentinel.core.engine import ModerationEngine
from sentinel.ml.baseline import SklearnToxicityModel
from sentinel.ml.transformer import TransformerToxicityModel


def build_moderation_engine() -> ModerationEngine:
    transformer_path = Path(
        os.getenv(
            "SENTINEL_TRANSFORMER_MODEL_PATH",
            "artifacts/models/transformer_toxicity",
        )
    )
    baseline_path = Path(
        os.getenv("SENTINEL_MODEL_PATH", "artifacts/models/toxicity_baseline.joblib")
    )
    if transformer_path.exists():
        toxicity_model = TransformerToxicityModel.load(transformer_path)
    elif baseline_path.exists():
        toxicity_model = SklearnToxicityModel.load(baseline_path)
    else:
        toxicity_model = None
    return ModerationEngine.default(toxicity_model=toxicity_model)
