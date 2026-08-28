from time import perf_counter

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


class SentinelMetrics:
    """Low-cardinality Prometheus metrics shared by API and worker processes."""

    def __init__(self, service: str) -> None:
        self.service = service
        self.registry = CollectorRegistry()
        self.build_info = Gauge(
            "sentinel_build_info",
            "Static Sentinel service build information.",
            ["service", "version"],
            registry=self.registry,
        )
        self.http_requests = Counter(
            "sentinel_http_requests_total",
            "HTTP requests handled by the API.",
            ["method", "route", "status_code"],
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "sentinel_http_request_duration_seconds",
            "HTTP request duration by templated route.",
            ["method", "route"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
            registry=self.registry,
        )
        self.inflight_requests = Gauge(
            "sentinel_http_inflight_requests",
            "HTTP requests currently being processed.",
            registry=self.registry,
        )
        self.decisions = Counter(
            "sentinel_moderation_decisions_total",
            "Moderation decisions emitted by decision path.",
            ["decision", "path"],
            registry=self.registry,
        )
        self.job_submissions = Counter(
            "sentinel_job_submissions_total",
            "Distributed moderation submission outcomes.",
            ["outcome"],
            registry=self.registry,
        )
        self.worker_events = Counter(
            "sentinel_worker_events_total",
            "Moderation worker event outcomes.",
            ["outcome"],
            registry=self.registry,
        )
        self.terminal_jobs = Counter(
            "sentinel_terminal_jobs_total",
            "Jobs reaching a terminal state.",
            ["state", "error_code"],
            registry=self.registry,
        )
        self.moderation_duration = Histogram(
            "sentinel_moderation_duration_seconds",
            "Core moderation evaluation duration.",
            ["path"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
            registry=self.registry,
        )
        self.review_events = Counter(
            "sentinel_review_events_total",
            "Human-review workflow event outcomes.",
            ["action", "outcome"],
            registry=self.registry,
        )
        self.review_backlog = Gauge(
            "sentinel_review_backlog",
            "Human-review cases by workflow state.",
            ["state"],
            registry=self.registry,
        )
        self.review_resolution_duration = Histogram(
            "sentinel_review_resolution_duration_seconds",
            "Elapsed time from review creation to a human decision.",
            buckets=(30, 60, 300, 900, 3600, 14400, 86400),
            registry=self.registry,
        )
        self.build_info.labels(service=service, version="0.1.0").set(1)

    @staticmethod
    def timer() -> float:
        return perf_counter()

    def record_http(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        self.http_requests.labels(method, route, str(status_code)).inc()
        self.http_duration.labels(method, route).observe(duration_seconds)

    def record_decision(self, decision: str, path: str) -> None:
        self.decisions.labels(decision, path).inc()

    def record_submission(self, outcome: str) -> None:
        self.job_submissions.labels(outcome).inc()

    def record_worker_event(self, outcome: str) -> None:
        self.worker_events.labels(outcome).inc()

    def record_terminal_job(self, state: str, error_code: str = "none") -> None:
        self.terminal_jobs.labels(state, error_code).inc()

    def record_review_event(self, action: str, outcome: str) -> None:
        self.review_events.labels(action, outcome).inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)


API_METRICS = SentinelMetrics("api")
WORKER_METRICS = SentinelMetrics("worker")
