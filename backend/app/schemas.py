"""API request / response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models import Job, JobStatus
from app.utils import is_valid_http_url


class DownloadRequest(BaseModel):
    url: str = Field(..., description="FlipBuilder index.html URL.")
    ocr: bool = Field(default=True)
    languages: str = Field(default="ind+eng")

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        value = value.strip()
        if not is_valid_http_url(value):
            raise ValueError("A valid http(s) URL is required.")
        return value

    @field_validator("languages")
    @classmethod
    def _validate_languages(cls, value: str) -> str:
        allowed = {"ind", "eng", "ind+eng", "eng+ind"}
        if value not in allowed:
            raise ValueError(f"languages must be one of {sorted(allowed)}")
        return value


class DownloadResponse(BaseModel):
    job_id: str


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    message: str
    title: Optional[str] = None
    current_page: int
    total_pages: int
    ocr: bool
    file_size: int = 0
    error: Optional[str] = None
    created_at: float
    updated_at: float
    download_url: Optional[str] = None

    # OCR detail fields
    ocr_current_page: int = 0
    ocr_total_pages: int = 0
    ocr_stage: str = ""
    ocr_start_time: float = 0.0

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        download_url = (
            f"/api/jobs/{job.id}/download"
            if job.status == JobStatus.COMPLETED and job.output_file
            else None
        )
        return cls(
            job_id=job.id,
            status=job.status,
            progress=job.progress,
            message=job.message,
            title=job.title,
            current_page=job.current_page,
            total_pages=job.total_pages,
            ocr=job.ocr,
            file_size=job.file_size,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at,
            download_url=download_url,
            ocr_current_page=job.ocr_current_page,
            ocr_total_pages=job.ocr_total_pages,
            ocr_stage=job.ocr_stage,
            ocr_start_time=job.ocr_start_time,
        )


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int


class HealthResponse(BaseModel):
    status: str = "ok"
    redis: bool
    tesseract: bool
    version: str
