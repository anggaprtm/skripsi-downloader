"""FlipBuilder / Flip PDF flipbook downloader.

Given a repository ``index.html`` URL this service:

1. Fetches ``javascript/config.js``
2. Extracts ``bookTitle``, ``totalPageCount``, ``normalPath`` and ``largePath``
3. Probes whether large images exist, otherwise falls back to mobile images
4. Downloads every page concurrently with retries
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import requests

from app.config import settings
from app.utils import base_url_from_index, get_logger, join_url

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int], None]

_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
_CONFIG_CANDIDATES = (
    # Most common FlipBuilder layouts
    "javascript/config.js",
    "config.js",
    # ir.unair.ac.id layout (config.js sits next to index.html)
    "mobile/javascript/config.js",
    "files/mobile/javascript/config.js",
    # Other known variants
    "js/config.js",
    "scripts/config.js",
    "assets/config.js",
)


class DownloaderError(RuntimeError):
    """Raised when a flipbook cannot be downloaded."""


@dataclass
class FlipbookMeta:
    """Metadata extracted from ``config.js``."""

    title: str
    total_pages: int
    base_url: str
    large_path: Optional[str] = None
    normal_path: Optional[str] = None


@dataclass
class DownloadResult:
    """Outcome of a successful page download run."""

    meta: FlipbookMeta
    files: list[Path] = field(default_factory=list)
    used_large: bool = False


class FlipbookDownloader:
    """Downloads all pages of a FlipBuilder flipbook."""

    def __init__(self, threads: Optional[int] = None) -> None:
        self.threads = threads or settings.default_download_threads
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.request_user_agent})

    # -- public API ---------------------------------------------------------
    def fetch_metadata(self, index_url: str) -> FlipbookMeta:
        base = base_url_from_index(index_url)
        config_text = self._fetch_config(base, index_url=index_url)
        title = self._extract_str(config_text, "bookTitle") or "Skripsi"
        total = self._extract_int(config_text, "totalPageCount") or self._extract_int(
            config_text, "pageCount"
        )
        if not total:
            raise DownloaderError("Could not detect totalPageCount in config.js")
        large_path = self._extract_str(config_text, "largePath")
        normal_path = self._extract_str(config_text, "normalPath")
        logger.info(
            "Metadata: title=%r pages=%s largePath=%r normalPath=%r",
            title,
            total,
            large_path,
            normal_path,
        )
        return FlipbookMeta(
            title=title.strip(),
            total_pages=total,
            base_url=base,
            large_path=large_path,
            normal_path=normal_path,
        )

    def download(
        self,
        index_url: str,
        dest_dir: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> DownloadResult:
        meta = self.fetch_metadata(index_url)
        url_template, used_large = self._resolve_template(meta)
        logger.info("Using %s images: %s", "LARGE" if used_large else "MOBILE", url_template)

        dest_dir.mkdir(parents=True, exist_ok=True)
        pad = len(str(meta.total_pages))
        results: dict[int, Path] = {}
        completed = 0

        def worker(page: int) -> tuple[int, Path]:
            url = url_template.format(n=page)
            target = dest_dir / f"page_{page:0{pad}d}.img"
            self._download_one(url, target)
            return page, target

        with ThreadPoolExecutor(max_workers=self.threads) as pool:
            futures = {pool.submit(worker, p): p for p in range(1, meta.total_pages + 1)}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    idx, path = future.result()
                    results[idx] = path
                except Exception as exc:  # noqa: BLE001 - report per-page failure
                    raise DownloaderError(f"Failed to download page {page}: {exc}") from exc
                completed += 1
                if progress:
                    progress(completed, meta.total_pages)

        ordered = [results[p] for p in sorted(results)]
        return DownloadResult(meta=meta, files=ordered, used_large=used_large)

    # -- config.js ----------------------------------------------------------
    def _fetch_config(self, base_url: str, index_url: str = "") -> str:
        """Fetch config.js content.

        Strategy (in order):
        1. Scrape index.html for a <script src="...config.js"> tag — this is
           the most reliable way to find it regardless of path layout.
        2. Fall through a list of known candidate paths.
        """
        # Step 1: try to extract the real path from index.html
        html_src = index_url or base_url.rstrip("/") + "/index.html"
        try:
            resp = self.session.get(html_src, timeout=settings.download_timeout)
            if resp.status_code == 200:
                # Match any <script src="...config.js"> or ...config.js?v=...
                matches = re.findall(
                    r'<script[^>]+src=["\']([^"\']*config\.js[^"\']*)["\']',
                    resp.text,
                    re.IGNORECASE,
                )
                for src in matches:
                    # src may be relative ("javascript/config.js") or absolute
                    if src.startswith("http"):
                        url = src
                    else:
                        url = join_url(base_url, src.split("?")[0])
                    try:
                        cr = self.session.get(url, timeout=settings.download_timeout)
                        if cr.status_code == 200 and cr.text:
                            logger.info("Loaded config from index.html scrape: %s", url)
                            return cr.text
                    except requests.RequestException:
                        continue
        except requests.RequestException:
            pass

        # Step 2: brute-force known candidate paths
        last_error: Optional[Exception] = None
        for candidate in _CONFIG_CANDIDATES:
            url = join_url(base_url, candidate)
            try:
                resp = self.session.get(url, timeout=settings.download_timeout)
                if resp.status_code == 200 and resp.text:
                    logger.info("Loaded config from candidate: %s", url)
                    return resp.text
            except requests.RequestException as exc:
                last_error = exc

        raise DownloaderError(
            f"Could not locate config.js near {base_url} "
            f"(tried {len(_CONFIG_CANDIDATES)} paths + index.html scrape; last error: {last_error})"
        )

    @staticmethod
    def _extract_str(text: str, key: str) -> Optional[str]:
        # Matches  key="value" | key:'value' | "key":"value" | key = `value`
        pattern = rf"""['"]?{re.escape(key)}['"]?\s*[:=]\s*['"`]([^'"`]*)['"`]"""
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @staticmethod
    def _extract_int(text: str, key: str) -> Optional[int]:
        pattern = rf"""['"]?{re.escape(key)}['"]?\s*[:=]\s*['"]?(\d+)"""
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None

    # -- image set resolution ----------------------------------------------
    def _resolve_template(self, meta: FlipbookMeta) -> tuple[str, bool]:
        """Return (url_template_with_{n}_and_ext, used_large)."""
        large_candidates = []
        if meta.large_path:
            large_candidates.append(meta.large_path)
        large_candidates.append("files/large/")

        normal_candidates = []
        if meta.normal_path:
            normal_candidates.append(meta.normal_path)
        normal_candidates.extend(["files/mobile/", "files/page/", "mobile/"])

        # Prefer large quality, fall back to mobile/normal.
        for rel in large_candidates:
            template = self._probe(meta.base_url, rel)
            if template:
                return template, True
        for rel in normal_candidates:
            template = self._probe(meta.base_url, rel)
            if template:
                return template, False

        raise DownloaderError("Could not locate page images (large or mobile).")

    def _probe(self, base_url: str, rel_path: str) -> Optional[str]:
        """Probe page 1 for each extension; return a format template if found."""
        for ext in _IMAGE_EXTENSIONS:
            url = join_url(base_url, rel_path, f"1.{ext}")
            try:
                resp = self.session.get(
                    url, timeout=settings.download_timeout, stream=True
                )
                content_type = resp.headers.get("Content-Type", "")
                if resp.status_code == 200 and "image" in content_type:
                    resp.close()
                    template = join_url(base_url, rel_path, f"{{n}}.{ext}")
                    return template
                resp.close()
            except requests.RequestException:
                continue
        return None

    # -- single page --------------------------------------------------------
    def _download_one(self, url: str, target: Path) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.download_retries + 1):
            try:
                resp = self.session.get(url, timeout=settings.download_timeout)
                if resp.status_code == 200 and resp.content:
                    target.write_bytes(resp.content)
                    return
                last_error = DownloaderError(f"HTTP {resp.status_code}")
            except requests.RequestException as exc:  # pragma: no cover - network
                last_error = exc
            time.sleep(min(2 ** attempt * 0.25, 4))
        raise DownloaderError(f"{url}: {last_error}")
