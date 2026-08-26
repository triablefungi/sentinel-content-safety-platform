import re
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from sentinel.observability.metrics import SentinelMetrics

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and measure every HTTP request."""

    def __init__(self, app, metrics: SentinelMetrics) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = (
            supplied_request_id
            if REQUEST_ID_PATTERN.fullmatch(supplied_request_id)
            else str(uuid4())
        )
        request.state.correlation_id = request_id
        started = perf_counter()
        status_code = 500
        self._metrics.inflight_requests.inc()
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            self._metrics.record_http(
                method=request.method,
                route=route_template,
                status_code=status_code,
                duration_seconds=perf_counter() - started,
            )
            self._metrics.inflight_requests.dec()
