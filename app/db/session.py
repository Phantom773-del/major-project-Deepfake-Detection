"""Async SQLAlchemy engine and session management.

Decision (documented in docs/BACKEND_IMPLEMENTATION.md): the application uses the
async SQLAlchemy 2.x stack with psycopg3. Alembic migrations run against a separate
sync engine (see ``app/db/migrations/env.py``).
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session per request."""
    async with SessionFactory() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose the engine pool (called on application shutdown)."""
    await engine.dispose()
