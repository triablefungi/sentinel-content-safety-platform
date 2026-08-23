from fastapi.testclient import TestClient

from sentinel.main import app


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

