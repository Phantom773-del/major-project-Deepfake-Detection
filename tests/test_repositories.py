"""Repository tests: create, retrieve, update, list (real PostgreSQL)."""

from app.db.models.media import Media
from app.db.models.model_version import ModelVersion
from app.db.models.scan import Scan
from app.domain.taxonomy import MediaType, ScanStatus, StageStatus
from app.repositories.media import MediaRepository
from app.repositories.model_version import ModelVersionRepository
from app.repositories.scan import ScanRepository
from sqlalchemy.ext.asyncio import AsyncSession


async def _media(db_session: AsyncSession) -> Media:
    return await MediaRepository(db_session).create(
        Media(original_filename="clip.mp4", media_type=MediaType.VIDEO, storage_path="ref-clip")
    )


async def test_model_version_repository_crud(db_session: AsyncSession) -> None:
    repo = ModelVersionRepository(db_session)
    created = await repo.create(
        ModelVersion(
            name="MediaPipe", version="v1.0", task="deepfake-facial", framework="mediapipe"
        )
    )
    got = await repo.get(created.id)
    assert got is not None and got.name == "MediaPipe"

    listed = await repo.list_all()
    assert any(m.id == created.id for m in listed)
    active = await repo.list_active()
    assert any(m.id == created.id for m in active)
    named = await repo.get_by_name_version("MediaPipe", "v1.0")
    assert named is not None and named.id == created.id


async def test_media_repository_crud_and_list(db_session: AsyncSession) -> None:
    repo = MediaRepository(db_session)
    first = await repo.create(await _media(db_session))
    await repo.create(await _media(db_session))

    got = await repo.get(first.id)
    assert got is not None and got.original_filename == "clip.mp4"

    items, total = await repo.list_all(page=1, page_size=1)
    assert total == 2
    assert len(items) == 1

    items2, _ = await repo.list_all(page=2, page_size=1)
    assert [m.id for m in items2] != [m.id for m in items]


async def test_scan_repository_create_get_update(db_session: AsyncSession) -> None:
    media = await _media(db_session)
    repo = ScanRepository(db_session)
    scan = Scan(media_id=media.id, status=ScanStatus.CREATED)
    stage = await repo.add_stage(scan, "validate", sequence=0)
    await repo.create(scan)

    got = await repo.get(scan.id)
    assert got is not None
    assert got.media.id == media.id
    assert [s.name for s in got.stages] == ["validate"]

    await repo.set_status(got, status=ScanStatus.VALIDATING)
    await repo.set_stage_status(stage, status=StageStatus.RUNNING)
    assert stage.status is StageStatus.RUNNING
    assert stage.started_at is not None

    items, total = await repo.list(page=1, page_size=10)
    assert total == 1
    assert items[0].id == scan.id
