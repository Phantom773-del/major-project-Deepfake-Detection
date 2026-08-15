"""FastAPI application factory for PHANTOM PHOENIX Backend."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine

logger = logging.getLogger(__name__)


def _ensure_directories(settings: Settings) -> None:
    """Create runtime directories (storage/reports) when not present."""
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        _ensure_directories(settings)
        logger.info(
            "Starting %s v%s (%s)", settings.app_name, settings.app_version, settings.app_env
        )
        yield
        await dispose_engine()
        logger.info("Shutdown complete")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Digital Media Authenticity & AI Forensic Intelligence Platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    register_exception_handlers(app)

    return app


app = create_app()
