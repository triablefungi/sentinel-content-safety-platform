import os
from dataclasses import dataclass
from pathlib import Path

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _positive_integer(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class SecuritySettings:
    environment: str = "development"
    docs_enabled: bool = True
    hsts_enabled: bool = False
    max_request_bytes: int = 8 * 1024 * 1024
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    rate_limit_max_clients: int = 10_000

    @classmethod
    def from_env(cls) -> "SecuritySettings":
        settings = cls(
            environment=os.getenv("SENTINEL_ENVIRONMENT", "development").strip().lower(),
            docs_enabled=_boolean("SENTINEL_DOCS_ENABLED", True),
            hsts_enabled=_boolean("SENTINEL_HSTS_ENABLED", False),
            max_request_bytes=_positive_integer(
                "SENTINEL_MAX_REQUEST_BYTES", 8 * 1024 * 1024
            ),
            rate_limit_enabled=_boolean("SENTINEL_RATE_LIMIT_ENABLED", False),
            rate_limit_requests=_positive_integer("SENTINEL_RATE_LIMIT_REQUESTS", 120),
            rate_limit_window_seconds=_positive_integer(
                "SENTINEL_RATE_LIMIT_WINDOW_SECONDS", 60
            ),
            rate_limit_max_clients=_positive_integer(
                "SENTINEL_RATE_LIMIT_MAX_CLIENTS", 10_000
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError(
                "SENTINEL_ENVIRONMENT must be development, test, or production"
            )
        if self.environment != "production":
            return
        if self.docs_enabled:
            raise ValueError("API documentation must be disabled in production")
        if not self.hsts_enabled:
            raise ValueError("HSTS must be enabled in production")
        if not self.rate_limit_enabled:
            raise ValueError("rate limiting must be enabled in production")
        review_enabled = _boolean("SENTINEL_REVIEW_ENABLED", False)
        review_auth_path = Path(
            os.getenv("SENTINEL_REVIEW_AUTH_PATH", "config/reviewer-auth.json")
        )
        if review_enabled and ".example." in review_auth_path.name:
            raise ValueError("development reviewer credentials cannot be used in production")
