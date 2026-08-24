from datetime import UTC, datetime

from fastapi.testclient import TestClient

from sentinel.distributed.adapters import InMemoryJobStore, RecordingEventPublisher
from sentinel.distributed.service import DistributedModerationService
from sentinel.main import app
from sentinel.schemas.moderation import JobState, ModerationJob


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_safe_text_is_allowed() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate/text",
            json={"text": "Thank you for sharing your perspective.", "request_id": "safe-1"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "allow"
    assert body["risk_score"] == 0.0
    assert body["signals"] == []


def test_explicit_threat_is_blocked() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate/text",
            json={"text": "I will kill you.", "request_id": "threat-1"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["decision"] == "block"
    assert body["signals"][0]["category"] == "threat"


def test_leetspeak_obfuscation_is_normalized() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderate/text",
            json={"text": "I will k1ll y0u."},
        )

    assert response.status_code == 200
    assert response.json()["decision"] == "block"


def test_blank_text_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/moderate/text", json={"text": "   "})

    assert response.status_code == 422


def test_distributed_endpoint_is_explicitly_unavailable_when_disabled() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/moderation/jobs",
            json={"text": "A queued test message", "request_id": "queue-disabled"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "distributed moderation is not enabled"


def test_distributed_submit_and_get_endpoints(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    service = DistributedModerationService(
        InMemoryJobStore(),
        RecordingEventPublisher(),
    )
    monkeypatch.setenv("SENTINEL_DISTRIBUTED_ENABLED", "true")
    monkeypatch.setattr(
        "sentinel.distributed.bootstrap.build_job_service_from_env",
        lambda: service,
    )

    with TestClient(app) as client:
        submitted = client.post(
            "/v1/moderation/jobs",
            json={"text": "A queued test message", "request_id": "queue-enabled"},
        )
        job_id = submitted.json()["job_id"]
        retrieved = client.get(f"/v1/moderation/jobs/{job_id}")

    assert submitted.status_code == 202
    assert submitted.json()["state"] == "accepted"
    assert retrieved.status_code == 200
    assert retrieved.json()["job_id"] == job_id


def test_distributed_job_not_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class MissingJobService:
        def submit(self, _request):  # type: ignore[no-untyped-def]
            return ModerationJob(
                job_id="unused",
                request_id="unused",
                state=JobState.ACCEPTED,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        def get(self, _job_id):  # type: ignore[no-untyped-def]
            return None

        def close(self) -> None:
            return None

    monkeypatch.setenv("SENTINEL_DISTRIBUTED_ENABLED", "true")
    monkeypatch.setattr(
        "sentinel.distributed.bootstrap.build_job_service_from_env",
        MissingJobService,
    )

    with TestClient(app) as client:
        response = client.get("/v1/moderation/jobs/missing")

    assert response.status_code == 404
