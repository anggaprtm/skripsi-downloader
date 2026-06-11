"""Application configuration.

All settings are read from environment variables (see ``.env.example``).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- General -----------------------------------------------------------
    app_name: str = "Skripsi Downloader"
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # --- API ---------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma separated list of allowed CORS origins.",
    )

    # --- Redis / Queue -----------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0")
    queue_name: str = Field(default="skripsi")
    job_timeout: int = Field(default=3600, description="RQ job timeout in seconds.")
    job_ttl: int = Field(default=86400, description="Result TTL in seconds (24h).")

    # --- Storage -----------------------------------------------------------
    storage_root: Path = Field(default=Path("/data"))
    job_retention_hours: int = Field(default=24)

    # --- Downloader --------------------------------------------------------
    default_download_threads: int = Field(default=20, alias="DEFAULT_DOWNLOAD_THREADS")
    download_retries: int = Field(default=3)
    download_timeout: int = Field(default=30)
    request_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 SkripsiDownloader/1.0"
        )
    )

    # --- OCR ---------------------------------------------------------------
    default_ocr_languages: str = Field(default="ind+eng")
    ocr_jobs: int = Field(default=2, description="Tesseract parallel jobs.")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def downloads_dir(self) -> Path:
        return self.storage_root / "downloads"

    @property
    def jobs_dir(self) -> Path:
        return self.storage_root / "jobs"

    @property
    def temp_dir(self) -> Path:
        return self.storage_root / "temp"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()


settings = get_settings()
