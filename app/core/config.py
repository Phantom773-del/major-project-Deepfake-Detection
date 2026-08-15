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
    report_dir: Path = Path("reports")
    max_upload_size_mb: int = 100

    # HTTP
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
