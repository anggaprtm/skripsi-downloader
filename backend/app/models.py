"""Internal domain models."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle states of a download job."""

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    BUILDING_PDF = "building_pdf"
    RUNNING_OCR = "running_ocr"
    COMPLETED = "completed"
    FAILED = "failed"


# Active (non-terminal) states.
ACTIVE_STATUSES = {
    JobStatus.QUEUED,
    JobStatus.DOWNLOADING,
    JobStatus.BUILDING_PDF,
    JobStatus.RUNNING_OCR,
}


class Job(BaseModel):
    """The full persisted state of a job."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    ocr: bool = True
    languages: str = "ind+eng"

    status: JobStatus = JobStatus.QUEUED
    progress: int = 0  # 0..100
    message: str = "Job queued"

    title: Optional[str] = None
    total_pages: int = 0
    current_page: int = 0

    # OCR detail tracking
    ocr_current_page: int = 0
    ocr_total_pages: int = 0
    ocr_start_time: float = 0.0   # epoch when OCR started
    ocr_stage: str = ""           # human-readable sub-stage

    output_file: Optional[str] = None
    file_size: int = 0
    error: Optional[str] = None

    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_redis(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_redis(cls, data: dict[str, Any]) -> "Job":
        return cls.model_validate(data)
