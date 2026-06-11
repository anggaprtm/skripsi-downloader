"""Job orchestration pipeline."""
from __future__ import annotations

import time

from app.downloader import DownloaderError, FlipbookDownloader
from app.models import Job, JobStatus
from app.ocr import OcrError, OcrService
from app.pdf import PdfError, PdfService
from app.storage import storage
from app.utils import get_logger, sanitize_filename

logger = get_logger(__name__)

_DOWNLOAD_WEIGHT = 65   # 0..65%
_PDF_DONE        = 72   # 72%
_OCR_START       = 73   # 73%
_OCR_DONE        = 100  # 100%
_OCR_RANGE       = _OCR_DONE - _OCR_START  # 27 points for OCR


class JobService:
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
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error in job %s", job_id)
            self._fail(job, f"Unexpected error: {exc}")

    def _run(self, job: Job) -> None:
        temp_dir = storage.temp_dir_for(job.id)

        # 1. Download -------------------------------------------------------
        self._update(job, status=JobStatus.DOWNLOADING, message="Membaca config.js", progress=0)
        last_percent = {"value": -1}

        def on_download(current: int, total: int) -> None:
            job.current_page = current
            job.total_pages = total
            percent = int(current / total * _DOWNLOAD_WEIGHT) if total else 0
            if percent != last_percent["value"]:
                last_percent["value"] = percent
                self._update(
                    job,
                    status=JobStatus.DOWNLOADING,
                    message=f"Mengunduh halaman {current} / {total}",
                    progress=percent,
                )

        result = self.downloader.download(job.url, temp_dir, progress=on_download)
        job.title = result.meta.title
        job.total_pages = result.meta.total_pages

        # 2. Build PDF ------------------------------------------------------
        self._update(
            job,
            status=JobStatus.BUILDING_PDF,
            message="Menyusun PDF dari gambar…",
            progress=_DOWNLOAD_WEIGHT,
            title=result.meta.title,
        )
        base_name = sanitize_filename(result.meta.title, fallback=f"skripsi_{job.id[:8]}")
        merged_pdf = temp_dir / f"{base_name}.merged.pdf"
        self.pdf.build(result.files, merged_pdf)
        self._update(
            job,
            status=JobStatus.BUILDING_PDF,
            message=f"PDF disusun ({result.meta.total_pages} halaman)",
            progress=_PDF_DONE,
        )

        downloads_dir = storage.downloads_dir()
        final_name = f"{job.id}__{base_name}.pdf"
        final_path = downloads_dir / final_name

        # 3. OCR (optional) -------------------------------------------------
        if job.ocr:
            job.ocr_start_time = time.time()
            job.ocr_total_pages = result.meta.total_pages
            job.ocr_current_page = 0
            self._update(
                job,
                status=JobStatus.RUNNING_OCR,
                message=f"Memulai OCR ({job.languages}) — {result.meta.total_pages} halaman",
                progress=_OCR_START,
                ocr_stage="Memulai OCR",
            )

            last_ocr = {"page": -1}

            def on_ocr(current: int, total: int, stage: str) -> None:
                job.ocr_current_page = current
                job.ocr_total_pages = total or result.meta.total_pages
                job.ocr_stage = stage

                # Calculate progress: OCR occupies _OCR_START.._OCR_DONE
                if total > 0:
                    ocr_frac = current / total
                else:
                    ocr_frac = 0
                progress = int(_OCR_START + ocr_frac * _OCR_RANGE)

                # Estimate remaining time
                elapsed = time.time() - job.ocr_start_time
                eta_str = ""
                if current > 1 and elapsed > 0:
                    rate = elapsed / current          # seconds per page
                    remaining = rate * (total - current)
                    if remaining < 60:
                        eta_str = f" (~{int(remaining)}d lagi)"
                    else:
                        eta_str = f" (~{int(remaining/60)}m lagi)"

                msg = f"OCR halaman {current} / {total} — {stage}{eta_str}"

                if current != last_ocr["page"]:
                    last_ocr["page"] = current
                    self._update(
                        job,
                        status=JobStatus.RUNNING_OCR,
                        message=msg,
                        progress=min(progress, _OCR_DONE - 1),
                        ocr_current_page=current,
                        ocr_total_pages=total,
                        ocr_stage=stage,
                    )

            self.ocr.run(
                merged_pdf, final_path,
                languages=job.languages,
                total_pages=result.meta.total_pages,
                on_progress=on_ocr,
            )
        else:
            merged_pdf.replace(final_path)

        # 4. Done -----------------------------------------------------------
        job.output_file = final_name
        job.file_size = final_path.stat().st_size if final_path.exists() else 0
        self._update(
            job,
            status=JobStatus.COMPLETED,
            message="Selesai ✓",
            progress=_OCR_DONE,
        )
        storage._cleanup_temp(job.id)  # noqa: SLF001
        logger.info("Job %s selesai -> %s (%d bytes)", job.id, final_name, job.file_size)

    def _update(self, job: Job, **fields) -> None:
        for key, value in fields.items():
            setattr(job, key, value)
        storage.save_job(job)

    def _fail(self, job: Job, error: str) -> None:
        job.status = JobStatus.FAILED
        job.error = error
        job.message = "Gagal"
        storage.save_job(job)
        storage._cleanup_temp(job.id)  # noqa: SLF001
        logger.error("Job %s gagal: %s", job.id, error)


def process_job(job_id: str) -> None:
    """RQ entrypoint."""
    JobService().run(job_id)
