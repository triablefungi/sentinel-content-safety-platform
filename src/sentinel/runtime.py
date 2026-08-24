import os
from pathlib import Path

from sentinel.core.engine import ModerationEngine
from sentinel.ml.baseline import SklearnToxicityModel
from sentinel.ml.transformer import TransformerToxicityModel
from sentinel.threat_intelligence.service import ThreatIntelligenceService


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
    threat_intelligence = _build_threat_intelligence()
    return ModerationEngine.default(
        toxicity_model=toxicity_model,
        threat_intelligence=threat_intelligence,
    )


def _build_threat_intelligence() -> ThreatIntelligenceService | None:
    qdrant_url = os.getenv("SENTINEL_QDRANT_URL")
    if not qdrant_url:
        return None

    from sentinel.threat_intelligence.adapters import QdrantThreatVectorStore
    from sentinel.threat_intelligence.encoder import HashedNgramEncoder

    encoder = HashedNgramEncoder(
        dimension=int(os.getenv("SENTINEL_THREAT_VECTOR_SIZE", "384"))
    )
    store = QdrantThreatVectorStore.connect(
        url=qdrant_url,
        collection_name=os.getenv(
            "SENTINEL_QDRANT_COLLECTION",
            "sentinel-threat-signals-v1",
        ),
        vector_size=encoder.dimension,
    )
    return ThreatIntelligenceService(
        encoder=encoder,
        store=store,
        similarity_threshold=float(
            os.getenv("SENTINEL_THREAT_SIMILARITY_THRESHOLD", "0.90")
        ),
    )
