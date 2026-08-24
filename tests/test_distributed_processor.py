from sentinel.core.engine import ModerationEngine
from sentinel.distributed.adapters import InMemoryJobStore, RecordingEventPublisher
from sentinel.distributed.processor import ModerationEventProcessor
from sentinel.schemas.moderation import (
    JobState,
    ModerationJob,
    ModerationJobEvent,
    ModerationRequest,
    StoredModerationJob,
)


class FailingEngine:
    def moderate(self, _request: ModerationRequest) -> None:
        raise RuntimeError("simulated model failure")


def create_event_and_store() -> tuple[ModerationJobEvent, InMemoryJobStore]:
    request = ModerationRequest(request_id="processor-test", text="A safe message")
    event = ModerationJobEvent(job_id="job-1", request=request)
    store = InMemoryJobStore()
    store.create(
        StoredModerationJob(
            job=ModerationJob(
                job_id=event.job_id,
                request_id="processor-test",
                state=JobState.ACCEPTED,
            ),
            request_fingerprint="test-fingerprint",
        )
    )
    return event, store


def test_successful_event_writes_result_and_terminal_state() -> None:
    event, store = create_event_and_store()
    publisher = RecordingEventPublisher()
    processor = ModerationEventProcessor(
        engine=ModerationEngine.default(),
        store=store,
        publisher=publisher,
    )

    processor.process(event)

    stored_job = store.get(event.job_id)
    assert stored_job is not None
    assert stored_job.job.state == JobState.SUCCEEDED
    assert stored_job.job.result is not None
    assert publisher.events[0]["topic"] == "sentinel.moderation.result.v1"


def test_failure_is_retried_before_attempt_limit() -> None:
    event, store = create_event_and_store()
    publisher = RecordingEventPublisher()
    processor = ModerationEventProcessor(
        engine=FailingEngine(),  # type: ignore[arg-type]
        store=store,
        publisher=publisher,
        max_attempts=3,
    )

    processor.process(event)

    stored_job = store.get(event.job_id)
    assert stored_job is not None
    assert stored_job.job.state == JobState.ACCEPTED
    assert stored_job.job.attempt == 1
    assert publisher.events[0]["topic"] == "sentinel.moderation.retry.v1"


def test_final_failure_is_sent_to_dlq() -> None:
    event, store = create_event_and_store()
    event = event.model_copy(update={"attempt": 2})
    publisher = RecordingEventPublisher()
    processor = ModerationEventProcessor(
        engine=FailingEngine(),  # type: ignore[arg-type]
        store=store,
        publisher=publisher,
        max_attempts=3,
    )

    processor.process(event)

    stored_job = store.get(event.job_id)
    assert stored_job is not None
    assert stored_job.job.state == JobState.FAILED
    assert stored_job.job.error_code == "processing_attempts_exhausted"
    assert publisher.events[0]["topic"] == "sentinel.moderation.dlq.v1"
