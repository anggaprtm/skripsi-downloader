"""Redis Queue (RQ) integration."""
from __future__ import annotations

from functools import lru_cache

import redis
from rq import Queue

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)


@lru_cache
def get_redis() -> redis.Redis:
    """Return a shared (binary) Redis connection for RQ."""
    return redis.Redis.from_url(settings.redis_url)


@lru_cache
def get_queue() -> Queue:
    """Return the shared RQ queue."""
    return Queue(
        settings.queue_name,
        connection=get_redis(),
        default_timeout=settings.job_timeout,
    )


def enqueue_download(job_id: str) -> str:
    """Enqueue a download job. The worker runs ``app.jobs.process_job``."""
    queue = get_queue()
    rq_job = queue.enqueue(
        "app.jobs.process_job",
        job_id,
        job_id=job_id,
        result_ttl=settings.job_ttl,
        failure_ttl=settings.job_ttl,
    )
    logger.info("Enqueued job %s", rq_job.id)
    return rq_job.id
