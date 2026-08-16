"""Shared test fixtures.

Point the application at the dedicated ``phantom_test`` database BEFORE importing
``app`` modules, because ``app/db/session.py`` builds its engine at import time.
"""

import os
import tempfile
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://phantom:phantom@localhost:5432/phantom_test",
)

MEDIA_ROOT = Path(tempfile.gettempdir()) / "phantom_media_tests"
os.environ.setdefault("MEDIA_STORAGE_ROOT", str(MEDIA_ROOT))

# Report artifacts root. ``STORAGE_DIR`` must be redirected too, or the report
# stage would write ``./storage/reports`` into the repository during tests.
REPORT_ROOT = Path(tempfile.gettempdir()) / "phantom_report_tests"
os.environ.setdefault("STORAGE_DIR", str(REPORT_ROOT))

from collections.abc import AsyncIterator, Iterator  # noqa: E402
from shutil import rmtree  # noqa: E402

import pytest  # noqa: E402
from app.main import create_app  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def media_storage_dir() -> Iterator[None]:
    """Fresh media and report storage directories for the whole test session."""
    rmtree(MEDIA_ROOT, ignore_errors=True)
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    rmtree(REPORT_ROOT, ignore_errors=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    yield
    rmtree(MEDIA_ROOT, ignore_errors=True)
    rmtree(REPORT_ROOT, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Iterator[None]:
    """Apply migrations to phantom_test once per session; drop schema on exit."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield

    import asyncio

    from app.db.session import engine

    async def _drop() -> None:
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))

    asyncio.run(_drop())


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    from app.db.session import SessionFactory

    async with SessionFactory() as session:
        yield session


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    """Truncate domain tables between tests for isolation."""
    yield
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE scan_stages, scans, media, model_versions RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    # Starlette 1.6 re-raises application exceptions after sending an error
    # response; raise_app_exceptions=False lets tests assert on the response body.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
