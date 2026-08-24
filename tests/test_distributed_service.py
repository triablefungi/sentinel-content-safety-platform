import pytest

from sentinel.distributed.adapters import InMemoryJobStore, RecordingEventPublisher
from sentinel.distributed.errors import IdempotencyConflictError, QueueUnavailableError
from sentinel.distributed.service import DistributedModerationService
from sentinel.schemas.moderation import JobState, ModerationRequest


def test_submit_is_idempotent_for_same_request() -> None:
    store = InMemoryJobStore()
    publisher = RecordingEventPublisher()
    service = DistributedModerationService(store, publisher)
    request = ModerationRequest(request_id="stable-request", text="A test message")

    first = service.submit(request)
    second = service.submit(request)

    assert first.job_id == second.job_id
    assert first.state == JobState.ACCEPTED
    assert len(publisher.events) == 1


def test_reused_request_id_with_different_content_is_rejected() -> None:
    service = DistributedModerationService(
        InMemoryJobStore(),
        RecordingEventPublisher(),
    )
    service.submit(ModerationRequest(request_id="duplicate", text="First message"))

    with pytest.raises(IdempotencyConflictError):
        service.submit(ModerationRequest(request_id="duplicate", text="Different message"))


def test_publish_failure_marks_job_failed() -> None:
    store = InMemoryJobStore()
    service = DistributedModerationService(
        store,
        RecordingEventPublisher(error=RuntimeError("broker unavailable")),
    )

    with pytest.raises(QueueUnavailableError):
        service.submit(ModerationRequest(request_id="publish-failure", text="Test"))

    stored_job = next(iter(store.jobs.values()))
    assert stored_job.job.state == JobState.FAILED
    assert stored_job.job.error_code == "queue_publish_failed"


def test_retry_after_publish_failure_reuses_job_id() -> None:
    store = InMemoryJobStore()
    failing_publisher = RecordingEventPublisher(error=RuntimeError("broker unavailable"))
    service = DistributedModerationService(store, failing_publisher)
    request = ModerationRequest(request_id="publish-retry", text="Test")

    with pytest.raises(QueueUnavailableError):
        service.submit(request)

    publisher = RecordingEventPublisher()
    retrying_service = DistributedModerationService(store, publisher)
    retried = retrying_service.submit(request)

    assert retried.state == JobState.ACCEPTED
    assert retried.error_code is None
    assert len(publisher.events) == 1
