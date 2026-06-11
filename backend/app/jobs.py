"""Job orchestration pipeline.

``process_job`` is the entrypoint executed by the RQ worker. It drives the
whole flow and continuously persists progress so the frontend can poll it.
"""
from __future__ import annotations

from app.downloader import DownloaderError, FlipbookDownloader
from app.models import Job, JobStatus
from app.ocr import OcrError, OcrService
from app.pdf import PdfError, PdfService
from app.storage import storage
from app.utils import get_logger, sanitize_filename

logger = get_logger(__name__)

# Progress weighting across stages.
_DOWNLOAD_WEIGHT = 70  # 0 .. 70 %
_PDF_DONE = 80
_OCR_DONE = 100


class JobService:
    """Runs a single job end to end."""

    def __init__(self) -> None:
        self.downloader = FlipbookDownloader()
        self.pdf = PdfService()
        self.ocr = OcrService()

    def run(self, job_id: str) -> None:
        job = storage.get_job(job_id)
        if job is None:
            logger.error("Job %s not found; aborting.", job_id)
            return
        try:
            self._run(job)
        except (DownloaderError, PdfError, OcrError) as exc:
            self._fail(job, str(exc))
        except Exception as exc:  # noqa: BLE001 - last-resort guard
            logger.exception("Unexpected error in job %s", job_id)
            self._fail(job, f"Unexpected error: {exc}")

    # -- pipeline -----------------------------------------------------------
    def _run(self, job: Job) -> None:
        temp_dir = storage.temp_dir_for(job.id)

        # 1. Download ------------------------------------------------------
        self._update(job, status=JobStatus.DOWNLOADING, message="Reading config.js", progress=0)
        last_percent = {"value": -1}

        def on_progress(current: int, total: int) -> None:
            job.current_page = current
            job.total_pages = total
            percent = int(current / total * _DOWNLOAD_WEIGHT) if total else 0
            if percent != last_percent["value"]:
                last_percent["value"] = percent
                self._update(
                    job,
                    status=JobStatus.DOWNLOADING,
                    message=f"Downloading page {current} / {total}",
                    progress=percent,
                )

        result = self.downloader.download(job.url, temp_dir, progress=on_progress)
        job.title = result.meta.title
        job.total_pages = result.meta.total_pages

        # 2. Build PDF -----------------------------------------------------
        self._update(
            job,
            status=JobStatus.BUILDING_PDF,
            message="Generating PDF",
            progress=_DOWNLOAD_WEIGHT,
            title=result.meta.title,
        )
        base_name = sanitize_filename(result.meta.title, fallback=f"skripsi_{job.id[:8]}")
        merged_pdf = temp_dir / f"{base_name}.merged.pdf"
        self.pdf.build(result.files, merged_pdf)
        self._update(job, status=JobStatus.BUILDING_PDF, message="PDF generated", progress=_PDF_DONE)

        downloads_dir = storage.downloads_dir()
        final_name = f"{job.id}__{base_name}.pdf"
        final_path = downloads_dir / final_name

        # 3. OCR (optional) ------------------------------------------------
        if job.ocr:
            self._update(
                job,
                status=JobStatus.RUNNING_OCR,
                message=f"Running OCR ({job.languages})",
                progress=_PDF_DONE + 5,
            )
            self.ocr.run(merged_pdf, final_path, languages=job.languages)
        else:
            merged_pdf.replace(final_path)

        # 4. Done ----------------------------------------------------------
        job.output_file = final_name
        job.file_size = final_path.stat().st_size if final_path.exists() else 0
        self._update(
            job,
            status=JobStatus.COMPLETED,
            message="Completed",
            progress=_OCR_DONE,
        )
        storage._cleanup_temp(job.id)  # noqa: SLF001 - intentional internal cleanup
        logger.info("Job %s completed -> %s (%d bytes)", job.id, final_name, job.file_size)

    # -- helpers ------------------------------------------------------------
    def _update(self, job: Job, **fields) -> None:
        for key, value in fields.items():
            setattr(job, key, value)
        storage.save_job(job)

    def _fail(self, job: Job, error: str) -> None:
        job.status = JobStatus.FAILED
        job.error = error
        job.message = "Failed"
        storage.save_job(job)
        storage._cleanup_temp(job.id)  # noqa: SLF001
        logger.error("Job %s failed: %s", job.id, error)


def process_job(job_id: str) -> None:
    """RQ entrypoint."""
    JobService().run(job_id)
