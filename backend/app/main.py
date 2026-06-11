"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import __version__
from app.config import settings
from app.models import Job, JobStatus
from app.ocr import OcrService
from app.queue import enqueue_download
from app.schemas import (
    DownloadRequest,
    DownloadResponse,
    HealthResponse,
    JobListResponse,
    JobResponse,
)
from app.storage import storage
from app.utils import get_logger, sanitize_filename

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.app_name, __version__)
    try:
        storage.cleanup_expired()
    except Exception:  # noqa: BLE001 - never block startup on cleanup
        logger.warning("Startup cleanup failed", exc_info=True)
    yield
    logger.info("Shutting down")


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(
        redis=storage.ping(),
        tesseract=OcrService.is_available(),
        version=__version__,
    )


@app.post("/api/download", response_model=DownloadResponse, tags=["jobs"])
def create_download(request: DownloadRequest) -> DownloadResponse:
    job = Job(url=request.url, ocr=request.ocr, languages=request.languages)
    storage.save_job(job)
    try:
        enqueue_download(job.id)
    except Exception as exc:  # noqa: BLE001
        job.status = JobStatus.FAILED
        job.error = f"Could not enqueue job: {exc}"
        job.message = "Failed"
        storage.save_job(job)
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc
    return DownloadResponse(job_id=job.id)


@app.get("/api/jobs", response_model=JobListResponse, tags=["jobs"])
def list_jobs() -> JobListResponse:
    jobs = storage.list_jobs()
    return JobListResponse(
        jobs=[JobResponse.from_job(job) for job in jobs],
        total=len(jobs),
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse, tags=["jobs"])
def get_job(job_id: str) -> JobResponse:
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobResponse.from_job(job)


@app.delete("/api/jobs/{job_id}", tags=["jobs"])
def delete_job(job_id: str) -> dict[str, str]:
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    storage.delete_job(job_id)
    return {"status": "deleted", "job_id": job_id}


@app.get("/api/jobs/{job_id}/download", tags=["jobs"])
def download_job(job_id: str) -> FileResponse:
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.status != JobStatus.COMPLETED or not job.output_file:
        raise HTTPException(status_code=409, detail="Job is not completed yet.")
    path = storage.output_path(job.output_file)
    if not path.exists():
        raise HTTPException(status_code=410, detail="File no longer available.")
    filename = f"{sanitize_filename(job.title or 'skripsi')}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": __version__, "docs": "/docs"}
