"""Scan application service: orchestration and lifecycle enforcement.

All status changes on a Scan go through this service, which enforces the
state machine defined in ``app/domain/scan.py``. API routes never set scan
status directly.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.scan import Scan, ScanStage
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.scan import STAGE_ORDER, assert_transition
from app.domain.taxonomy import ScanStatus, StageStatus
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository


class ScanService:
    """Domain service for the scan lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.scans = ScanRepository(session)
        self.media = MediaRepository(session)

    async def create_scan(self, *, media_id: uuid.UUID) -> Scan:
        """Create a case record (CREATED) with pending stages. No analysis runs."""
        media = await self.media.get(media_id)
        if media is None or media.is_deleted:
            raise NotFoundError("media not found")
        scan = Scan(media_id=media_id, status=ScanStatus.CREATED)
        scan.stages = [
            ScanStage(name=name, status=StageStatus.PENDING, sequence=sequence)
            for sequence, name in enumerate(STAGE_ORDER)
        ]
        return await self.scans.create(scan)

    async def get_scan(self, *, scan_id: uuid.UUID) -> Scan:
        scan = await self.scans.get(scan_id)
        if scan is None:
            raise NotFoundError("scan not found")
        return scan

    async def list_scans(
        self,
        *,
        page: int,
        page_size: int,
        status: ScanStatus | None = None,
    ) -> tuple[list[Scan], int]:
        return await self.scans.list(page=page, page_size=page_size, status=status)

    async def transition(
        self,
        scan: Scan,
        *,
        to: ScanStatus,
        error: str | None = None,
    ) -> Scan:
        """Apply an allowed status transition, updating timestamps as needed."""
        assert_transition(scan.status, to)
        if to is ScanStatus.PROCESSING and scan.started_at is None:
            scan.started_at = datetime.now(UTC)
        if to is ScanStatus.COMPLETED:
            scan.completed_at = datetime.now(UTC)
        if to is ScanStatus.FAILED:
            scan.error_message = error
            scan.completed_at = datetime.now(UTC)
        return await self.scans.set_status(scan, status=to)

    async def mark_stage(
        self,
        scan: Scan,
        *,
        name: str,
        status: StageStatus,
        error: str | None = None,
        result_ref: str | None = None,
    ) -> ScanStage:
        """Update the status of a stage on a scan; error if unknown stage."""
        stage = next((s for s in scan.stages if s.name == name), None)
        if stage is None:
            raise NotFoundError(f"scan stage {name!r} not found")
        if status is StageStatus.FAILED and error is None:
            raise ConflictError("a failed stage requires an error message")
        return await self.scans.set_stage_status(
            stage, status=status, error=error, result_ref=result_ref
        )
