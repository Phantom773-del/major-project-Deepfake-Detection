"""Shared test fixtures.

Point the application at the dedicated ``phantom_test`` database BEFORE importing
``app`` modules, because ``app/db/session.py`` builds its engine at import time.
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://phantom:phantom@localhost:5432/phantom_test",
)

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from app.main import create_app  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


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
