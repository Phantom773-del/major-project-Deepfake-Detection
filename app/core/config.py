"""Application configuration.

Centralized settings loaded from environment variables and an optional ``.env`` file.
Secrets are never hard-coded; production values are supplied via environment.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the PHANTOM PHOENIX backend.

    Every field can be overridden through environment variables (case-insensitive)
    or an optional ``.env`` file (see ``.env.example``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_env: str = "development"
    app_name: str = "PHANTOM PHOENIX Backend"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+psycopg://phantom:phantom@localhost:5432/phantom"

    # Auth (reserved for the authentication milestone)
    # Development placeholder only — real environments must override via env var.
    secret_key: str = "change-me"  # noqa: S105
    access_token_expire_minutes: int = 60

    # Storage
    storage_dir: Path = Path("storage")
    media_storage_root: Path = Path("storage/media")
    report_dir: Path = Path("reports")
    max_upload_size_mb: int = 50

    # Upload allowlists (server-side detection is authoritative; client
    # Content-Type / filename extension are never trusted).
    # Video list is empty until a real video ingestion pipeline exists.
    allowed_image_mime_types: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
    )
    allowed_video_mime_types: tuple[str, ...] = ()

    # Analysis worker (in-process v1; replaceable by Celery later)
    analysis_worker_enabled: bool = False
    analysis_worker_poll_interval_seconds: float = 1.0

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    # HTTP
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
