"""Domain model tests: creation, relationships, constraints (real PostgreSQL)."""

import pytest
from app.db.models.media import Media
from app.db.models.model_version import ModelVersion
from app.db.models.scan import Scan, ScanStage
from app.domain.taxonomy import MediaType, ModelVersionStatus, ScanStatus, StageStatus
from app.repositories.media import MediaRepository
from app.repositories.model_version import ModelVersionRepository
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def test_model_version_coexists_distinct_versions(db_session: AsyncSession) -> None:
    repo = ModelVersionRepository(db_session)
    a = await repo.create(
        ModelVersion(
            name="EfficientNet-B4",
            version="v0.1",
            task="image-authenticity-detection",
            framework="pytorch",
        )
    )
    b = await repo.create(
        ModelVersion(
            name="EfficientNet-B4",
            version="v0.2",
            task="image-authenticity-detection",
            framework="pytorch",
        )
    )
    assert a.id != b.id
    assert a.status is ModelVersionStatus.ACTIVE
    assert b.configuration == {}
    got = await repo.get_by_name_version("EfficientNet-B4", "v0.1")
    assert got is not None and got.id == a.id


async def test_model_version_unique_name_version_pair(db_session: AsyncSession) -> None:
    repo = ModelVersionRepository(db_session)
    await repo.create(
        ModelVersion(name="EfficientNet-B4", version="v0.1", task="image-authenticity-detection")
    )
    with pytest.raises(IntegrityError):
        await repo.create(
            ModelVersion(
                name="EfficientNet-B4", version="v0.1", task="image-authenticity-detection"
            )
        )
    await db_session.rollback()


async def test_media_creation_and_fields(db_session: AsyncSession) -> None:
    media = await MediaRepository(db_session).create(
        Media(
            original_filename="sample.png",
            media_type=MediaType.IMAGE,
            mime_type="image/png",
            size_bytes=1024,
            sha256="a" * 64,
            width=640,
            height=480,
            storage_path="s3://bucket/uuid-123",
        )
    )
    assert media.id is not None
    assert media.is_deleted is False
    assert media.sha256 == "a" * 64


async def test_scan_relationships_and_stage_cascade(db_session: AsyncSession) -> None:
    media = await MediaRepository(db_session).create(
        Media(original_filename="a.png", media_type=MediaType.IMAGE, storage_path="ref-a")
    )
    scan = Scan(media_id=media.id, status=ScanStatus.CREATED)
    scan.stages = [
        ScanStage(name="validate", status=StageStatus.PENDING, sequence=0),
        ScanStage(name="detect", status=StageStatus.PENDING, sequence=1),
    ]
    db_session.add(scan)
    await db_session.flush()

    assert scan.media.id == media.id
    assert [s.name for s in scan.stages] == ["validate", "detect"]

    scan_id = scan.id
    await db_session.delete(scan)
    await db_session.flush()

    remaining = (
        await db_session.scalars(select(ScanStage).where(ScanStage.scan_id == scan_id))
    ).all()
    assert remaining == []
