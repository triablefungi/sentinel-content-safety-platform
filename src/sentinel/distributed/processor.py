import json
from datetime import UTC, datetime

from sentinel.core.engine import ModerationEngine
from sentinel.distributed.protocols import EventPublisher, JobStore
from sentinel.schemas.moderation import (
    JobState,
    ModerationJobEvent,
    StoredModerationJob,
)


class ModerationEventProcessor:
    """Process one event with bounded retry and terminal DLQ handling."""

    def __init__(
        self,
        engine: ModerationEngine,
        store: JobStore,
        publisher: EventPublisher,
        retry_topic: str = "sentinel.moderation.retry.v1",
        result_topic: str = "sentinel.moderation.result.v1",
        dlq_topic: str = "sentinel.moderation.dlq.v1",
        max_attempts: int = 3,
    ) -> None:
        self._engine = engine
        self._store = store
        self._publisher = publisher
        self._retry_topic = retry_topic
        self._result_topic = result_topic
        self._dlq_topic = dlq_topic
        self._max_attempts = max_attempts

    def process(self, event: ModerationJobEvent) -> None:
        stored_job = self._store.get(event.job_id)
        if stored_job is None:
            self._publish_dlq(event, "missing_job_state")
            return
        if stored_job.job.state == JobState.SUCCEEDED:
            return

        processing = self._with_job_update(
            stored_job,
            state=JobState.PROCESSING,
            attempt=event.attempt,
            error_code=None,
        )
        self._store.save(processing)

        try:
            result = self._engine.moderate(event.request)
        except Exception:
            self._handle_failure(event, processing)
            return

        self._publisher.publish(
            topic=self._result_topic,
            key=event.job_id,
            payload=result.model_dump_json().encode("utf-8"),
        )
        succeeded = self._with_job_update(
            processing,
            state=JobState.SUCCEEDED,
            attempt=event.attempt,
            result=result,
            error_code=None,
        )
        self._store.save(succeeded)

    def close(self) -> None:
        self._publisher.close()
        self._store.close()

    def _handle_failure(
        self,
        event: ModerationJobEvent,
        stored_job: StoredModerationJob,
    ) -> None:
        next_attempt = event.attempt + 1
        if next_attempt < self._max_attempts:
            retry_event = event.model_copy(update={"attempt": next_attempt})
            self._publisher.publish(
                topic=self._retry_topic,
                key=event.job_id,
                payload=retry_event.model_dump_json().encode("utf-8"),
            )
            retrying = self._with_job_update(
                stored_job,
                state=JobState.ACCEPTED,
                attempt=next_attempt,
                error_code="processing_retry_scheduled",
            )
            self._store.save(retrying)
            return

        self._publish_dlq(event, "processing_attempts_exhausted")
        failed = self._with_job_update(
            stored_job,
            state=JobState.FAILED,
            attempt=event.attempt,
            error_code="processing_attempts_exhausted",
        )
        self._store.save(failed)

    def _publish_dlq(self, event: ModerationJobEvent, error_code: str) -> None:
        payload = {
            "job_id": event.job_id,
            "request_id": event.request.request_id,
            "attempt": event.attempt,
            "error_code": error_code,
        }
        self._publisher.publish(
            topic=self._dlq_topic,
            key=event.job_id,
            payload=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        )

    @staticmethod
    def _with_job_update(
        stored_job: StoredModerationJob,
        **updates: object,
    ) -> StoredModerationJob:
        updates["updated_at"] = datetime.now(UTC)
        return stored_job.model_copy(
            update={"job": stored_job.job.model_copy(update=updates)}
        )
