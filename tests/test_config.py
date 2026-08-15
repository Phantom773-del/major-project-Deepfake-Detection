"""Tests for application configuration loading."""

import pytest
from app.core.config import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_name == "PHANTOM PHOENIX Backend"
    assert settings.app_version == "0.1.0"
    assert settings.app_env == "development"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.max_upload_size_mb == 50
    assert settings.access_token_expire_minutes == 60
    assert settings.storage_dir.name == "storage"
    assert settings.report_dir.name == "reports"


def test_environment_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Override Name")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "250")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)
    assert settings.app_name == "Override Name"
    assert settings.max_upload_size_mb == 250
    assert settings.log_level == "DEBUG"


def test_cors_origins_parse_from_env_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://app.example.com"]


def test_get_settings_singleton() -> None:
    from app.core.config import get_settings

    assert get_settings() is get_settings()
