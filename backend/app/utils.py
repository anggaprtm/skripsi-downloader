"""Shared helper utilities."""
from __future__ import annotations

import logging
import re
import sys
import unicodedata
from urllib.parse import urlparse

from app.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure root logging once, idempotently."""
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger."""
    configure_logging()
    return logging.getLogger(name)


def sanitize_filename(value: str, fallback: str = "skripsi") -> str:
    """Turn an arbitrary title into a safe, ascii filesystem name."""
    if not value:
        return fallback
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s.-]", "", value).strip()
    value = re.sub(r"[\s_-]+", "_", value)
    value = value.strip("._")
    return value[:120] or fallback


def base_url_from_index(index_url: str) -> str:
    """Return the directory base URL from a ``.../index.html`` url.

    ``https://host/path/index.html`` -> ``https://host/path/``
    """
    parsed = urlparse(index_url)
    path = parsed.path
    if path.endswith(".html") or path.endswith(".htm"):
        path = path.rsplit("/", 1)[0] + "/"
    elif not path.endswith("/"):
        path = path + "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def join_url(base: str, *parts: str) -> str:
    """Join URL parts safely onto a base directory URL.

    Unlike ``urljoin``, this never drops base path segments that look like
    opaque tokens (e.g. base64-encoded directory names such as ``YzJm...w==/``).
    """
    # Ensure base ends with /
    url = base if base.endswith("/") else base + "/"
    for part in parts:
        # Strip leading slashes so we always append relative to base
        part = part.lstrip("/")
        if not part:
            continue
        url = url + part if url.endswith("/") else url + "/" + part
        # If the part itself doesn't end with / and more parts follow, let
        # the next iteration add the slash.
    return url


def is_valid_http_url(value: str) -> bool:
    """Validate that ``value`` is an http(s) URL."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False
