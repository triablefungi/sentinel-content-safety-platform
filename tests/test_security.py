from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from sentinel.security import ProductionSecurityMiddleware, SecuritySettings


def secured_app(settings: SecuritySettings) -> FastAPI:
    app = FastAPI()
    app.add_middleware(ProductionSecurityMiddleware, settings=settings)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/resource")
    async def resource() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/echo")
    async def echo(request: Request) -> dict[str, object]:
        return await request.json()

    return app


def test_security_headers_are_applied() -> None:
    with TestClient(secured_app(SecuritySettings())) as client:
        response = client.get("/resource")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_small_request_body_remains_available_to_endpoint() -> None:
    settings = SecuritySettings(max_request_bytes=128)
    with TestClient(secured_app(settings)) as client:
        response = client.post("/echo", json={"message": "small"})

    assert response.status_code == 200
    assert response.json() == {"message": "small"}


def test_oversized_request_is_rejected_before_endpoint() -> None:
    settings = SecuritySettings(max_request_bytes=16)
    with TestClient(secured_app(settings)) as client:
        response = client.post("/echo", json={"message": "x" * 32})

    assert response.status_code == 413
    assert response.json()["detail"] == "request body exceeds the configured limit"


def test_rate_limit_and_operational_exemption() -> None:
    settings = SecuritySettings(
        rate_limit_enabled=True,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )
    with TestClient(secured_app(settings)) as client:
        first = client.get("/resource")
        second = client.get("/resource")
        rejected = client.get("/resource")
        health = client.get("/health")

    assert first.status_code == 200
    assert first.headers["ratelimit-remaining"] == "1"
    assert second.status_code == 200
    assert rejected.status_code == 429
    assert rejected.headers["retry-after"]
    assert health.status_code == 200


def test_production_settings_require_security_controls(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SENTINEL_ENVIRONMENT", "production")

    try:
        SecuritySettings.from_env()
    except ValueError as error:
        assert "documentation must be disabled" in str(error)
    else:
        raise AssertionError("insecure production settings were accepted")


def test_production_rejects_example_reviewer_credentials(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("SENTINEL_ENVIRONMENT", "production")
    monkeypatch.setenv("SENTINEL_DOCS_ENABLED", "false")
    monkeypatch.setenv("SENTINEL_HSTS_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_REVIEW_ENABLED", "true")
    monkeypatch.setenv(
        "SENTINEL_REVIEW_AUTH_PATH", "config/reviewer-auth.example.json"
    )

    try:
        SecuritySettings.from_env()
    except ValueError as error:
        assert "development reviewer credentials" in str(error)
    else:
        raise AssertionError("example reviewer credentials were accepted in production")
