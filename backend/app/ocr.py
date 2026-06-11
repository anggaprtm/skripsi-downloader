"""OCR service with real-time per-page progress tracking."""
from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from app.config import settings
from app.utils import get_logger

logger = get_logger(__name__)

_ALLOWED_LANGS = {"ind", "eng", "ind+eng", "eng+ind"}

# Patterns in ocrmypdf --verbose 1 output that signal page processing
_PAGE_PATTERN = re.compile(r"(?:OCR|processing|page)\s+(\d+)", re.IGNORECASE)
_STAGE_PATTERNS = [
    (re.compile(r"orient", re.IGNORECASE),        "Mendeteksi orientasi halaman"),
    (re.compile(r"deskew", re.IGNORECASE),         "Meluruskan halaman"),
    (re.compile(r"clean", re.IGNORECASE),          "Membersihkan gambar"),
    (re.compile(r"tesseract", re.IGNORECASE),      "Tesseract OCR"),
    (re.compile(r"optim", re.IGNORECASE),          "Mengoptimasi PDF"),
    (re.compile(r"assembl|output", re.IGNORECASE), "Menyusun PDF akhir"),
]

OcrProgressCallback = Callable[[int, int, str], None]


class OcrError(RuntimeError):
    pass


class OcrService:
    @staticmethod
    def is_available() -> bool:
        return shutil.which("ocrmypdf") is not None and shutil.which("tesseract") is not None

    def run(
        self,
        source: Path,
        output: Path,
        languages: str = "ind+eng",
        total_pages: int = 0,
        on_progress: Optional[OcrProgressCallback] = None,
    ) -> Path:
        if languages not in _ALLOWED_LANGS:
            languages = settings.default_ocr_languages
        if not self.is_available():
            raise OcrError("ocrmypdf / tesseract not installed.")

        output.parent.mkdir(parents=True, exist_ok=True)

        rc, detail = self._run_cmd(
            source, output, languages,
            extra_flags=["--optimize", "1", "--output-type", "pdf"],
            total_pages=total_pages,
            on_progress=on_progress,
        )
        if rc == 0:
            logger.info("OCR complete -> %s", output.name)
            return output

        if rc in (15, 10, 6):
            logger.warning("ocrmypdf exit %d, retrying without optimization...", rc)
            output.unlink(missing_ok=True)
            rc2, detail2 = self._run_cmd(
                source, output, languages,
                extra_flags=["--optimize", "0", "--output-type", "pdf", "--skip-big", "250"],
                total_pages=total_pages,
                on_progress=on_progress,
            )
            if rc2 == 0:
                logger.info("OCR complete (fallback) -> %s", output.name)
                return output
            raise OcrError(f"ocrmypdf failed on retry (exit {rc2}): {detail2[:500]}")

        raise OcrError(f"ocrmypdf exited {rc}: {detail[:500]}")

    def _run_cmd(
        self,
        source: Path,
        output: Path,
        languages: str,
        extra_flags: list[str] | None = None,
        total_pages: int = 0,
        on_progress: Optional[OcrProgressCallback] = None,
    ) -> tuple[int, str]:
        cmd = [
            "ocrmypdf",
            "--force-ocr",
            "-l", languages,
            "--jobs", str(settings.ocr_jobs),
            "--verbose", "1",   # enables per-page output we can parse
            *(extra_flags or []),
            str(source),
            str(output),
        ]
        logger.info("Running OCR: %s", " ".join(cmd))

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise OcrError(f"Failed to start ocrmypdf: {exc}") from exc

        output_lines: list[str] = []
        current_page = 0
        last_stage = "Memulai OCR"

        def _reader() -> None:
            nonlocal current_page, last_stage
            assert proc.stdout
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                output_lines.append(line)
                logger.debug("ocrmypdf: %s", line)

                # Detect page number from output
                m = _PAGE_PATTERN.search(line)
                if m:
                    page_num = int(m.group(1))
                    if page_num != current_page:
                        current_page = page_num
                        if on_progress:
                            on_progress(current_page, total_pages or current_page, last_stage)

                # Detect stage
                for pattern, label in _STAGE_PATTERNS:
                    if pattern.search(line):
                        last_stage = label
                        if on_progress:
                            on_progress(current_page, total_pages or 1, last_stage)
                        break

        reader_thread = threading.Thread(target=_reader, daemon=True)
        reader_thread.start()

        try:
            proc.wait(timeout=settings.job_timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise OcrError("OCR timed out.")
        finally:
            reader_thread.join(timeout=5)

        detail = "\n".join(output_lines[-20:])
        return proc.returncode, detail
