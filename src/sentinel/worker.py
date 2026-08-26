import json
import os
import signal
from types import FrameType
from typing import Any

from prometheus_client import start_http_server
from pydantic import ValidationError

from sentinel.distributed.adapters import KafkaEventPublisher, RedisJobStore
from sentinel.distributed.processor import ModerationEventProcessor
from sentinel.observability.metrics import WORKER_METRICS
from sentinel.runtime import build_moderation_engine
from sentinel.schemas.moderation import ModerationJobEvent


def build_processor() -> ModerationEventProcessor:
    bootstrap_servers = os.getenv("SENTINEL_KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    redis_url = os.getenv("SENTINEL_REDIS_URL", "redis://localhost:6379/0")
    ttl_seconds = int(os.getenv("SENTINEL_JOB_TTL_SECONDS", "86400"))
    publisher = KafkaEventPublisher.connect(
        bootstrap_servers=bootstrap_servers,
        client_id="sentinel-worker",
    )
    return ModerationEventProcessor(
        engine=build_moderation_engine(),
        store=RedisJobStore.from_url(redis_url, ttl_seconds=ttl_seconds),
        publisher=publisher,
        retry_topic=os.getenv("SENTINEL_RETRY_TOPIC", "sentinel.moderation.retry.v1"),
        result_topic=os.getenv("SENTINEL_RESULT_TOPIC", "sentinel.moderation.result.v1"),
        dlq_topic=os.getenv("SENTINEL_DLQ_TOPIC", "sentinel.moderation.dlq.v1"),
        max_attempts=int(os.getenv("SENTINEL_MAX_ATTEMPTS", "3")),
        metrics=WORKER_METRICS,
    )


def build_consumer() -> Any:
    from confluent_kafka import Consumer

    return Consumer(
        {
            "bootstrap.servers": os.getenv(
                "SENTINEL_KAFKA_BOOTSTRAP_SERVERS",
                "localhost:29092",
            ),
            "group.id": os.getenv(
                "SENTINEL_KAFKA_CONSUMER_GROUP",
                "sentinel-moderation-workers-v1",
            ),
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


def run() -> None:
    start_http_server(
        int(os.getenv("SENTINEL_WORKER_METRICS_PORT", "9101")),
        registry=WORKER_METRICS.registry,
    )
    consumer = build_consumer()
    processor = build_processor()
    input_topic = os.getenv("SENTINEL_INPUT_TOPIC", "sentinel.moderation.input.v1")
    retry_topic = os.getenv("SENTINEL_RETRY_TOPIC", "sentinel.moderation.retry.v1")
    dlq_topic = os.getenv("SENTINEL_DLQ_TOPIC", "sentinel.moderation.dlq.v1")
    invalid_event_publisher = KafkaEventPublisher.connect(
        bootstrap_servers=os.getenv(
            "SENTINEL_KAFKA_BOOTSTRAP_SERVERS",
            "localhost:29092",
        ),
        client_id="sentinel-worker-invalid-events",
    )
    running = True

    def stop(_signal_number: int, _frame: FrameType | None) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    consumer.subscribe([input_topic, retry_topic])

    try:
        while running:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(str(message.error()))
            try:
                event = ModerationJobEvent.model_validate_json(message.value())
            except ValidationError:
                WORKER_METRICS.record_worker_event("invalid_event_schema")
                WORKER_METRICS.record_terminal_job("failed", "invalid_event_schema")
                invalid_payload = json.dumps(
                    {
                        "error_code": "invalid_event_schema",
                        "source_topic": message.topic(),
                        "partition": message.partition(),
                        "offset": message.offset(),
                    },
                    separators=(",", ":"),
                ).encode("utf-8")
                invalid_event_publisher.publish(
                    topic=dlq_topic,
                    key=f"invalid-{message.partition()}-{message.offset()}",
                    payload=invalid_payload,
                )
                consumer.commit(message=message, asynchronous=False)
                continue

            processor.process(event)
            consumer.commit(message=message, asynchronous=False)
    finally:
        consumer.close()
        invalid_event_publisher.close()
        processor.close()


if __name__ == "__main__":
    run()
