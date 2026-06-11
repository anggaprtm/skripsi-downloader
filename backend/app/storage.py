"""Persistence layer.

Job state lives in Redis so the API and worker processes share a single
source of truth. Generated PDFs live on the ``downloads`` volume.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import redis

from app.config import settings
from app.models import Job
from app.utils import get_logger

logger = get_logger(__name__)

_JOB_KEY_PREFIX = "skripsi:job:"
_JOB_INDEX_KEY = "skripsi:jobs"  # sorted set of job ids scored by created_at


class StorageService:
    """Manages job metadata in Redis and files on disk."""

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self._redis = redis_client or redis.Redis.from_url(
            settings.redis_url, decode_responses=True
        )
        self._ensure_dirs()

    # -- filesystem ---------------------------------------------------------
    def _ensure_dirs(self) -> None:
        for directory in (settings.downloads_dir, settings.jobs_dir, settings.temp_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def temp_dir_for(self, job_id: str) -> Path:
        path = settings.temp_dir / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def downloads_dir(self) -> Path:
        settings.downloads_dir.mkdir(parents=True, exist_ok=True)
        return settings.downloads_dir

    def output_path(self, relative: str) -> Path:
        return settings.downloads_dir / relative

    # -- redis job state ----------------------------------------------------
    @staticmethod
    def _key(job_id: str) -> str:
        return f"{_JOB_KEY_PREFIX}{job_id}"

    def save_job(self, job: Job) -> Job:
        job.touch()
        payload = json.dumps(job.to_redis())
        pipe = self._redis.pipeline()
        pipe.set(self._key(job.id), payload, ex=settings.job_retention_hours * 3600)
        pipe.zadd(_JOB_INDEX_KEY, {job.id: job.created_at})
        pipe.execute()
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        raw = self._redis.get(self._key(job_id))
        if not raw:
            return None
        try:
            return Job.from_redis(json.loads(raw))
        except (ValueError, TypeError) as exc:  # pragma: no cover - defensive
            logger.error("Failed to decode job %s: %s", job_id, exc)
            return None

    def list_jobs(self, limit: int = 200) -> list[Job]:
        job_ids = self._redis.zrevrange(_JOB_INDEX_KEY, 0, limit - 1)
        jobs: list[Job] = []
        stale: list[str] = []
        for job_id in job_ids:
            job = self.get_job(job_id)
            if job is None:
                stale.append(job_id)
                continue
            jobs.append(job)
        if stale:
            self._redis.zrem(_JOB_INDEX_KEY, *stale)
        return jobs

    def delete_job(self, job_id: str) -> None:
        job = self.get_job(job_id)
        self._redis.delete(self._key(job_id))
        self._redis.zrem(_JOB_INDEX_KEY, job_id)
        if job and job.output_file:
            self._safe_unlink(self.output_path(job.output_file))
        self._cleanup_temp(job_id)

    # -- cleanup ------------------------------------------------------------
    def cleanup_expired(self) -> int:
        """Remove jobs older than the retention window. Returns count removed."""
        cutoff = time.time() - settings.job_retention_hours * 3600
        expired_ids = self._redis.zrangebyscore(_JOB_INDEX_KEY, 0, cutoff)
        removed = 0
        for job_id in expired_ids:
            self.delete_job(job_id)
            removed += 1
        # Sweep orphaned temp directories as well.
        if settings.temp_dir.exists():
            for entry in settings.temp_dir.iterdir():
                try:
                    if entry.is_dir() and entry.stat().st_mtime < cutoff:
                        self._cleanup_temp(entry.name)
                except OSError:  # pragma: no cover - defensive
                    continue
        if removed:
            logger.info("Cleanup removed %d expired job(s)", removed)
        return removed

    def _cleanup_temp(self, job_id: str) -> None:
        import shutil

        path = settings.temp_dir / job_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:  # pragma: no cover - defensive
            logger.warning("Could not delete file %s", path)

    # -- health -------------------------------------------------------------
    def ping(self) -> bool:
        try:
            return bool(self._redis.ping())
        except redis.RedisError:
            return False


# Module-level singleton used by the API and worker.
storage = StorageService()
