from collections.abc import Mapping
from typing import Any

from sentinel.schemas.moderation import StoredModerationJob


class RedisJobStore:
    """Redis-backed state store with atomic create-if-absent idempotency."""

    def __init__(self, client: Any, ttl_seconds: int = 86_400) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_url(cls, url: str, ttl_seconds: int = 86_400) -> "RedisJobStore":
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        return cls(client=client, ttl_seconds=ttl_seconds)

    def create(self, stored_job: StoredModerationJob) -> bool:
        result = self._client.set(
            self._key(stored_job.job.job_id),
            stored_job.model_dump_json(),
            nx=True,
            ex=self._ttl_seconds,
        )
        return bool(result)

    def get(self, job_id: str) -> StoredModerationJob | None:
        payload = self._client.get(self._key(job_id))
        if payload is None:
            return None
        return StoredModerationJob.model_validate_json(payload)

    def save(self, stored_job: StoredModerationJob) -> None:
        self._client.set(
            self._key(stored_job.job.job_id),
            stored_job.model_dump_json(),
            xx=True,
            ex=self._ttl_seconds,
        )

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _key(job_id: str) -> str:
        return f"sentinel:moderation:job:{job_id}"


class KafkaEventPublisher:
    """Kafka producer that waits for an all-replica delivery acknowledgement."""

    def __init__(self, producer: Any, delivery_timeout_seconds: float = 10.0) -> None:
        self._producer = producer
        self._delivery_timeout_seconds = delivery_timeout_seconds

    @classmethod
    def connect(
        cls,
        bootstrap_servers: str,
        client_id: str,
        delivery_timeout_seconds: float = 10.0,
    ) -> "KafkaEventPublisher":
        from confluent_kafka import Producer

        producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "client.id": client_id,
                "acks": "all",
                "enable.idempotence": True,
                "message.timeout.ms": int(delivery_timeout_seconds * 1_000),
            }
        )
        return cls(producer, delivery_timeout_seconds=delivery_timeout_seconds)

    def publish(self, topic: str, key: str, payload: bytes) -> None:
        delivery_error: list[str] = []

        def on_delivery(error: object | None, _message: object) -> None:
            if error is not None:
                delivery_error.append(str(error))

        self._producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=payload,
            on_delivery=on_delivery,
        )
        remaining = self._producer.flush(self._delivery_timeout_seconds)
        if delivery_error:
            raise RuntimeError(delivery_error[0])
        if remaining:
            raise TimeoutError(f"{remaining} Kafka event(s) were not acknowledged")

    def close(self) -> None:
        self._producer.flush(self._delivery_timeout_seconds)


class InMemoryJobStore:
    """Deterministic test adapter implementing the same idempotency contract."""

    def __init__(self) -> None:
        self.jobs: dict[str, StoredModerationJob] = {}

    def create(self, stored_job: StoredModerationJob) -> bool:
        if stored_job.job.job_id in self.jobs:
            return False
        self.jobs[stored_job.job.job_id] = stored_job
        return True

    def get(self, job_id: str) -> StoredModerationJob | None:
        return self.jobs.get(job_id)

    def save(self, stored_job: StoredModerationJob) -> None:
        self.jobs[stored_job.job.job_id] = stored_job

    def close(self) -> None:
        return None


class RecordingEventPublisher:
    """Test adapter that records published events."""

    def __init__(self, error: Exception | None = None) -> None:
        self.events: list[Mapping[str, object]] = []
        self._error = error

    def publish(self, topic: str, key: str, payload: bytes) -> None:
        if self._error is not None:
            raise self._error
        self.events.append({"topic": topic, "key": key, "payload": payload})

    def close(self) -> None:
        return None
