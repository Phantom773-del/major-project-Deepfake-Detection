"""Tests for SQLAlchemy database infrastructure.

These are integration tests against the real PostgreSQL test database
(``phantom_test``, see tests/conftest.py). They require the dev container
running via ``docker compose up -d postgres``.
"""

from app.db.base import Base
from app.db.session import SessionFactory, engine
from sqlalchemy import text


async def test_engine_connects() -> None:
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


async def test_session_factory_runs_query() -> None:
    async with SessionFactory() as session:
        result = await session.execute(text("SELECT current_database()"))
        assert result.scalar_one() == "phantom_test"


async def test_base_metadata_create_and_drop() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with engine.connect() as connection:
            tables = await connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            assert tables.all() == []
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
