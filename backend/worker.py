"""RQ worker entrypoint.

Run with:  python worker.py
"""
from __future__ import annotations

from rq import Worker

from app.config import settings
from app.queue import get_queue, get_redis
from app.storage import storage
from app.utils import get_logger

logger = get_logger("worker")


def main() -> None:
    logger.info("Worker starting on queue %r", settings.queue_name)
    # Opportunistic cleanup of expired jobs at worker boot.
    try:
        storage.cleanup_expired()
    except Exception:  # noqa: BLE001
        logger.warning("Cleanup at boot failed", exc_info=True)

    queue = get_queue()
    worker = Worker([queue], connection=get_redis())
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
