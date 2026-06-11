"""PDF assembly service.

Merges downloaded page images into a single PDF. Images are normalised with
Pillow first because ``img2pdf`` rejects images with alpha channels or unusual
colour profiles.
"""
from __future__ import annotations

from pathlib import Path

import img2pdf
from PIL import Image

from app.utils import get_logger

logger = get_logger(__name__)

Image.MAX_IMAGE_PIXELS = None  # repository scans can be very large


class PdfError(RuntimeError):
    """Raised when a PDF cannot be assembled."""


class PdfService:
    """Builds a PDF from a list of image files."""

    def build(self, images: list[Path], output: Path) -> Path:
        if not images:
            raise PdfError("No images supplied for PDF assembly.")

        normalized: list[str] = []
        for image_path in images:
            normalized.append(str(self._normalize(image_path)))

        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output.open("wb") as fh:
                fh.write(img2pdf.convert(normalized))
        except Exception as exc:  # noqa: BLE001
            raise PdfError(f"img2pdf failed: {exc}") from exc

        logger.info("Built PDF %s (%d pages)", output.name, len(images))
        return output

    @staticmethod
    def _normalize(image_path: Path) -> Path:
        """Ensure an image is a flat RGB JPEG that img2pdf accepts."""
        normalized_path = image_path.with_suffix(".norm.jpg")
        try:
            with Image.open(image_path) as img:
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    converted = img.convert("RGBA")
                    background.paste(converted, mask=converted.split()[-1])
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(normalized_path, "JPEG", quality=92)
        except Exception as exc:  # noqa: BLE001
            raise PdfError(f"Could not process image {image_path.name}: {exc}") from exc
        return normalized_path
