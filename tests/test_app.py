"""Tests for the FastAPI application factory."""

from app.main import create_app
from fastapi import FastAPI


def test_app_factory_returns_configured_app() -> None:
    app: FastAPI = create_app()
    assert app.title == "PHANTOM PHOENIX Backend"
    assert app.version == "0.1.0"
    assert app.redoc_url is not None


def test_v1_router_mounted() -> None:
    app: FastAPI = create_app()
    # FastAPI 1.6 nests included routers; url_path_for exercises the full stack.
    assert app.url_path_for("health") == "/api/v1/health"


def test_global_app_instance_exists() -> None:
    import app.main as main

    assert main.app is not None
    assert main.app.title == "PHANTOM PHOENIX Backend"
