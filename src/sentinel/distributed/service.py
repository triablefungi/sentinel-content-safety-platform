import hashlib
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from sentinel.distributed.errors import IdempotencyConflictError, QueueUnavailableError
from sentinel.distributed.protocols import EventPublisher, JobStore
from sentinel.schemas.moderation import (
    JobState,
    ModerationJob,
    ModerationJobEvent,
    ModerationRequest,
    StoredModerationJob,
)


class DistributedModerationService:
    """Submit idempotent moderation jobs and retrieve their state."""

    def __init__(
        self,
        store: JobStore,
        publisher: EventPublisher,
        input_topic: str = "sentinel.moderation.input.v1",
    ) -> None:
        self._store = store
        self._publisher = publisher
        self._input_topic = input_topic

    def submit(self, request: ModerationRequest) -> ModerationJob:
        request_id = request.request_id or str(uuid4())
        normalized_request = request.model_copy(update={"request_id": request_id})
        fingerprint = self._fingerprint(normalized_request)
        job_id = str(uuid5(NAMESPACE_URL, f"sentinel:{request_id}"))
        now = datetime.now(UTC)
        stored_job = StoredModerationJob(
            job=ModerationJob(
                job_id=job_id,
                request_id=request_id,
                state=JobState.ACCEPTED,
                created_at=now,
                updated_at=now,
            ),
            request_fingerprint=fingerprint,
        )

        if not self._store.create(stored_job):
            existing = self._store.get(job_id)
            if existing is None:
                raise QueueUnavailableError("job state disappeared during idempotency check")
            if existing.request_fingerprint != fingerprint:
                raise IdempotencyConflictError(request_id)
            if (
                existing.job.state == JobState.FAILED
                and existing.job.error_code == "queue_publish_failed"
            ):
                event = ModerationJobEvent(job_id=job_id, request=normalized_request)
                self._publish_or_fail(existing, event)
                accepted = existing.model_copy(
                    update={
                        "job": existing.job.model_copy(
                            update={
                                "state": JobState.ACCEPTED,
                                "error_code": None,
                                "updated_at": datetime.now(UTC),
                            }
                        )
                    }
                )
                self._store.save(accepted)
                return accepted.job
            return existing.job

        event = ModerationJobEvent(job_id=job_id, request=normalized_request)
        self._publish_or_fail(stored_job, event)
        return stored_job.job

    def _publish_or_fail(
        self,
        stored_job: StoredModerationJob,
        event: ModerationJobEvent,
    ) -> None:
        try:
            self._publisher.publish(
                topic=self._input_topic,
                key=event.job_id,
                payload=event.model_dump_json().encode("utf-8"),
            )
        except Exception as exc:
            failed = stored_job.model_copy(
                update={
                    "job": stored_job.job.model_copy(
                        update={
                            "state": JobState.FAILED,
                            "error_code": "queue_publish_failed",
                            "updated_at": datetime.now(UTC),
                        }
                    )
                }
            )
            self._store.save(failed)
            raise QueueUnavailableError("broker did not acknowledge moderation job") from exc

    def get(self, job_id: str) -> ModerationJob | None:
        stored_job = self._store.get(job_id)
        return stored_job.job if stored_job is not None else None

    def close(self) -> None:
        self._publisher.close()
        self._store.close()

    @staticmethod
    def _fingerprint(request: ModerationRequest) -> str:
        canonical = request.model_dump_json(exclude_none=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
