import asyncio
import math
from dataclasses import dataclass
from time import monotonic

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from sentinel.security.config import SecuritySettings

EXEMPT_PATHS = frozenset({"/health", "/health/ready", "/metrics"})
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


@dataclass
class _TokenBucket:
    tokens: float
    updated_at: float


class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    """Apply bounded request handling, local rate limiting, and security headers."""

    def __init__(self, app, settings: SecuritySettings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._settings = settings
        self._buckets: dict[str, _TokenBucket] = {}
        self._bucket_lock = asyncio.Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        rejection = await self._reject_oversized_request(request)
        if rejection is None:
            rejection = await self._reject_rate_limited_request(request)
        response = rejection if rejection is not None else await call_next(request)
        self._apply_security_headers(request, response)
        return response

    async def _reject_oversized_request(self, request: Request) -> Response | None:
        if request.method not in BODY_METHODS:
            return None
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                return self._error(400, "content-length must be an integer")
            if declared_size < 0:
                return self._error(400, "content-length must not be negative")
            if declared_size > self._settings.max_request_bytes:
                return self._error(413, "request body exceeds the configured limit")

        chunks: list[bytes] = []
        received = 0
        async for chunk in request.stream():
            received += len(chunk)
            if received > self._settings.max_request_bytes:
                return self._error(413, "request body exceeds the configured limit")
            chunks.append(chunk)
        request._body = b"".join(chunks)  # noqa: SLF001 - Starlette cached-body contract
        return None

    async def _reject_rate_limited_request(self, request: Request) -> Response | None:
        if not self._settings.rate_limit_enabled or request.url.path in EXEMPT_PATHS:
            return None
        allowed, remaining, retry_after = await self._consume_token(self._client_key(request))
        if allowed:
            request.state.rate_limit_remaining = remaining
            return None
        response = self._error(429, "request rate limit exceeded")
        response.headers["Retry-After"] = str(retry_after)
        response.headers["RateLimit-Limit"] = str(self._settings.rate_limit_requests)
        response.headers["RateLimit-Remaining"] = "0"
        response.headers["RateLimit-Reset"] = str(retry_after)
        return response

    async def _consume_token(self, client_key: str) -> tuple[bool, int, int]:
        now = monotonic()
        capacity = float(self._settings.rate_limit_requests)
        refill_per_second = capacity / self._settings.rate_limit_window_seconds
        async with self._bucket_lock:
            bucket = self._buckets.get(client_key)
            if bucket is None:
                self._prune_buckets(now)
                if len(self._buckets) >= self._settings.rate_limit_max_clients:
                    client_key = "__overflow__"
                bucket = self._buckets.setdefault(client_key, _TokenBucket(capacity, now))
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(capacity, bucket.tokens + elapsed * refill_per_second)
            bucket.updated_at = now
            if bucket.tokens < 1:
                retry_after = max(1, math.ceil((1 - bucket.tokens) / refill_per_second))
                return False, 0, retry_after
            bucket.tokens -= 1
            return True, math.floor(bucket.tokens), 0

    def _prune_buckets(self, now: float) -> None:
        stale_after = self._settings.rate_limit_window_seconds * 2
        stale = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.updated_at > stale_after
        ]
        for key in stale:
            del self._buckets[key]

    @staticmethod
    def _client_key(request: Request) -> str:
        return request.client.host if request.client is not None else "unknown"

    def _apply_security_headers(self, request: Request, response: Response) -> None:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            )
        if self._settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        remaining = getattr(request.state, "rate_limit_remaining", None)
        if remaining is not None:
            response.headers["RateLimit-Limit"] = str(self._settings.rate_limit_requests)
            response.headers["RateLimit-Remaining"] = str(remaining)
            response.headers["RateLimit-Reset"] = str(
                self._settings.rate_limit_window_seconds
            )

    @staticmethod
    def _error(status_code: int, detail: str) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": detail})
