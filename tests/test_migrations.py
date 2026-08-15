"""Migration tests: applied schema exists in the real test database."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EXPECTED_TABLES = {
    "media",
    "model_versions",
    "scans",
    "scan_stages",
    "alembic_version",
}

EXPECTED_ENUMS = {"media_type", "model_version_status", "scan_status", "stage_status"}


async def test_all_tables_exist(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public'"
        )
    )
    tables = {row[0] for row in result.all()}
    assert EXPECTED_TABLES <= tables


async def test_required_enums_exist(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT typname FROM pg_type "
            "WHERE typname IN ('media_type', 'model_version_status', 'scan_status', 'stage_status')"
        )
    )
    enums = {row[0] for row in result.all()}
    assert EXPECTED_ENUMS <= enums


async def test_scan_tables_have_expected_columns(db_session: AsyncSession) -> None:
    expected_scan = {"id", "media_id", "status", "started_at", "completed_at", "error_message"}
    expected_stage = {
        "id",
        "scan_id",
        "name",
        "status",
        "sequence",
        "started_at",
        "completed_at",
        "duration_ms",
        "error_message",
        "result_ref",
    }
    for table, expected in (("scans", expected_scan), ("scan_stages", expected_stage)):
        result = await db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table"
            ),
            {"table": table},
        )
        columns = {row[0] for row in result.all()}
        assert expected <= columns
