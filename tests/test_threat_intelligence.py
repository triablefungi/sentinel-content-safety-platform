from sentinel.core.engine import ModerationEngine
from sentinel.schemas.moderation import ModerationRequest
from sentinel.threat_intelligence.adapters import InMemoryThreatVectorStore
from sentinel.threat_intelligence.encoder import HashedNgramEncoder
from sentinel.threat_intelligence.service import ThreatIntelligenceService


def build_engine() -> ModerationEngine:
    intelligence = ThreatIntelligenceService(
        encoder=HashedNgramEncoder(),
        store=InMemoryThreatVectorStore(),
    )
    return ModerationEngine.default(threat_intelligence=intelligence)


def test_encoder_normalizes_common_obfuscation() -> None:
    encoder = HashedNgramEncoder()

    assert encoder.encode("I will k1ll y0u") == encoder.encode("I will kill you")


def test_third_repeated_message_is_escalated_for_review() -> None:
    engine = build_engine()
    text = "Limited offer available now. Click to claim your reward."

    first = engine.moderate(ModerationRequest(request_id="campaign-1", text=text))
    second = engine.moderate(ModerationRequest(request_id="campaign-2", text=text))
    third = engine.moderate(ModerationRequest(request_id="campaign-3", text=text))

    assert first.decision == "allow"
    assert second.decision == "allow"
    assert third.decision == "review"
    assert third.signals[0].category == "coordinated_abuse"
    assert third.signals[0].reason_code == "similar_content_campaign"


def test_repeated_campaign_reaches_block_threshold() -> None:
    engine = build_engine()
    text = "Repeated coordinated campaign payload."

    for index in range(5):
        engine.moderate(
            ModerationRequest(request_id=f"campaign-block-{index}", text=text)
        )
    result = engine.moderate(
        ModerationRequest(request_id="campaign-block-final", text=text)
    )

    assert result.decision == "block"
    assert result.risk_score == 0.90


def test_same_request_id_does_not_count_itself_as_campaign() -> None:
    engine = build_engine()
    request = ModerationRequest(request_id="same-id", text="A repeated request")

    first = engine.moderate(request)
    duplicate = engine.moderate(request)

    assert first.decision == "allow"
    assert duplicate.decision == "allow"
