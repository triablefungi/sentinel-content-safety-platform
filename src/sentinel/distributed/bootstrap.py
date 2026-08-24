import os

from sentinel.distributed.adapters import KafkaEventPublisher, RedisJobStore
from sentinel.distributed.service import DistributedModerationService


def build_job_service_from_env() -> DistributedModerationService:
    bootstrap_servers = os.getenv("SENTINEL_KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    redis_url = os.getenv("SENTINEL_REDIS_URL", "redis://localhost:6379/0")
    input_topic = os.getenv("SENTINEL_INPUT_TOPIC", "sentinel.moderation.input.v1")
    ttl_seconds = int(os.getenv("SENTINEL_JOB_TTL_SECONDS", "86400"))
    store = RedisJobStore.from_url(redis_url, ttl_seconds=ttl_seconds)
    publisher = KafkaEventPublisher.connect(
        bootstrap_servers=bootstrap_servers,
        client_id="sentinel-api",
    )
    return DistributedModerationService(
        store=store,
        publisher=publisher,
        input_topic=input_topic,
    )
