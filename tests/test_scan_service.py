"""Scan lifecycle service tests: valid/invalid state machine transitions."""

import uuid

import pytest
from app.db.models.media import Media
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import MediaType, ScanStatus, StageStatus
from app.repositories.media import MediaRepository
from app.services.scans import ScanService
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_media(db_session: AsyncSession) -> Media:
    return await MediaRepository(db_session).create(
        Media(original_filename="a.png", media_type=MediaType.IMAGE, storage_path="ref-a")
    )


async def test_create_scan_builds_case_with_pending_stages(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    assert scan.status is ScanStatus.CREATED
    assert [s.name for s in scan.stages] == list(STAGE_ORDER)
    assert all(s.status is StageStatus.PENDING for s in scan.stages)
    assert [s.sequence for s in scan.stages] == list(range(len(STAGE_ORDER)))


async def test_create_scan_unknown_media_raises(db_session: AsyncSession) -> None:
    service = ScanService(db_session)
    with pytest.raises(NotFoundError):
        await service.create_scan(media_id=uuid.uuid4())


async def test_valid_transition_path_to_completion(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    await service.transition(scan, to=ScanStatus.VALIDATING)
    await service.transition(scan, to=ScanStatus.QUEUED)
    await service.transition(scan, to=ScanStatus.PROCESSING)
    await service.transition(scan, to=ScanStatus.COMPLETED)

    assert scan.status is ScanStatus.COMPLETED
    assert scan.started_at is not None
    assert scan.completed_at is not None


async def test_failure_transition_sets_error(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    await service.transition(scan, to=ScanStatus.VALIDATING)
    await service.transition(scan, to=ScanStatus.FAILED, error="validation rejected media")

    assert scan.status is ScanStatus.FAILED
    assert scan.error_message == "validation rejected media"
    assert scan.completed_at is not None


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (ScanStatus.CREATED, ScanStatus.COMPLETED),
        (ScanStatus.CREATED, ScanStatus.PROCESSING),
        (ScanStatus.CREATED, ScanStatus.QUEUED),
        (ScanStatus.VALIDATING, ScanStatus.COMPLETED),
        (ScanStatus.QUEUED, ScanStatus.COMPLETED),
        (ScanStatus.PROCESSING, ScanStatus.VALIDATING),
    ],
)
async def test_invalid_transitions_rejected(
    db_session: AsyncSession, source: ScanStatus, target: ScanStatus
) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)
    scan.status = source
    await db_session.flush()

    with pytest.raises(ConflictError):
        await service.transition(scan, to=target)


async def test_failed_scan_is_terminal_no_retry(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)
    await service.transition(scan, to=ScanStatus.VALIDATING)
    await service.transition(scan, to=ScanStatus.FAILED, error="boom")

    with pytest.raises(ConflictError):
        await service.transition(scan, to=ScanStatus.PROCESSING)


async def test_same_status_transition_rejected(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    with pytest.raises(ConflictError):
        await service.transition(scan, to=ScanStatus.CREATED)


async def test_mark_stage_lifecycle(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    stage = await service.mark_stage(scan, name="validate", status=StageStatus.RUNNING)
    assert stage.status is StageStatus.RUNNING
    assert stage.started_at is not None

    await service.mark_stage(scan, name="validate", status=StageStatus.COMPLETED)
    assert stage.completed_at is not None
    assert stage.duration_ms is not None


async def test_mark_unknown_stage_raises(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    with pytest.raises(NotFoundError):
        await service.mark_stage(scan, name="does-not-exist", status=StageStatus.RUNNING)


async def test_fail_stage_requires_error(db_session: AsyncSession) -> None:
    media = await _create_media(db_session)
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)

    with pytest.raises(ConflictError):
        await service.mark_stage(scan, name="validate", status=StageStatus.FAILED)
