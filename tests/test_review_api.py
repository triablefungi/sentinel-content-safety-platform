import hashlib

from fastapi.testclient import TestClient

from sentinel.main import app
from sentinel.review.auth import ReviewAuthorizer
from sentinel.review.models import ReviewerRole, ReviewPrincipal
from sentinel.review.repository import InMemoryReviewRepository
from sentinel.review.service import ReviewService

REVIEWER_TOKEN = "reviewer-api-secret"
AUDITOR_TOKEN = "auditor-api-secret"


def review_system() -> tuple[ReviewService, ReviewAuthorizer]:
    authorizer = ReviewAuthorizer(
        {
            hashlib.sha256(REVIEWER_TOKEN.encode()).hexdigest(): ReviewPrincipal(
                reviewer_id="reviewer-api",
                role=ReviewerRole.REVIEWER,
            ),
            hashlib.sha256(AUDITOR_TOKEN.encode()).hexdigest(): ReviewPrincipal(
                reviewer_id="auditor-api",
                role=ReviewerRole.AUDITOR,
            ),
        }
    )
    return ReviewService(InMemoryReviewRepository()), authorizer


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_review_api_end_to_end(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("sentinel.main.build_review_system", review_system)

    with TestClient(app) as client:
        moderated = client.post(
            "/v1/moderate/text",
            json={"request_id": "review-api-1", "text": "You are worthless."},
        )
        listed = client.get("/v1/reviews?state=pending", headers=bearer(REVIEWER_TOKEN))
        metrics = client.get("/metrics")
        case_id = listed.json()[0]["case_id"]
        claimed = client.post(
            f"/v1/reviews/{case_id}/claim",
            headers=bearer(REVIEWER_TOKEN),
        )
        decided = client.post(
            f"/v1/reviews/{case_id}/decisions",
            headers=bearer(REVIEWER_TOKEN),
            json={"decision": "block", "reason_code": "confirmed_abuse"},
        )
        audit = client.get(
            f"/v1/reviews/{case_id}/audit",
            headers=bearer(AUDITOR_TOKEN),
        )
        exported = client.get(
            "/v1/review-feedback/export",
            headers=bearer(AUDITOR_TOKEN),
        )

    assert moderated.json()["decision"] == "review"
    assert len(listed.json()) == 1
    assert 'sentinel_review_backlog{state="pending"} 1.0' in metrics.text
    assert claimed.json()["state"] == "claimed"
    assert decided.json()["state"] == "resolved"
    assert len(audit.json()) == 3
    assert exported.json()["records"][0]["human_decision"] == "block"
    assert "text" not in exported.text


def test_review_api_requires_bearer_token(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("sentinel.main.build_review_system", review_system)

    with TestClient(app) as client:
        response = client.get("/v1/reviews")

    assert response.status_code == 401


def test_reviewer_cannot_export_feedback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("sentinel.main.build_review_system", review_system)

    with TestClient(app) as client:
        response = client.get(
            "/v1/review-feedback/export",
            headers=bearer(REVIEWER_TOKEN),
        )

    assert response.status_code == 403
