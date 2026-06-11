"""OCR service.

Runs ``ocrmypdf`` against an assembled PDF to produce a searchable PDF.
OCR is optional and controlled per-job from the frontend.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)

_ALLOWED_LANGS = {"ind", "eng", "ind+eng", "eng+ind"}


class OcrError(RuntimeError):
    """Raised when OCR processing fails."""


class OcrService:
    """Thin wrapper around the ocrmypdf CLI."""

    @staticmethod
    def is_available() -> bool:
        return shutil.which("ocrmypdf") is not None and shutil.which("tesseract") is not None

    def run(self, source: Path, output: Path, languages: str = "ind+eng") -> Path:
        if languages not in _ALLOWED_LANGS:
            languages = settings.default_ocr_languages
        if not self.is_available():
            raise OcrError("ocrmypdf / tesseract not installed in this environment.")

        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ocrmypdf",
            "--force-ocr",
            "-l",
            languages,
            "--jobs",
            str(settings.ocr_jobs),
            "--optimize",
            "1",
            "--quiet",
            str(source),
            str(output),
        ]
        logger.info("Running OCR: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.job_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise OcrError("OCR timed out.") from exc

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "unknown error").strip()
            raise OcrError(f"ocrmypdf exited {proc.returncode}: {detail[:500]}")

        logger.info("OCR complete -> %s", output.name)
        return output
