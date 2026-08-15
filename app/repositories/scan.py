"""Scan and ScanStage repository."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.scan import Scan, ScanStage
from app.domain.taxonomy import ScanStatus, StageStatus
from app.repositories.base import Repository


class ScanRepository(Repository[Scan]):
    model = Scan

    async def get(self, entity_id: uuid.UUID) -> Scan | None:
        """Fetch a scan with its media and stages eagerly loaded."""
        stmt = (
            select(Scan)
            .options(joinedload(Scan.media), selectinload(Scan.stages))
            .where(Scan.id == entity_id)
        )
        result = await self.session.scalar(stmt)
        if result is None:
            return None
        return result

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        status: ScanStatus | None = None,
    ) -> tuple[list[Scan], int]:
        base = select(Scan)
        count_base = select(func.count(Scan.id))
        if status is not None:
            base = base.where(Scan.status == status)
            count_base = count_base.where(Scan.status == status)
        total = await self.session.scalar(count_base)
        if total is None:
            total = 0
        stmt = (
            base.options(joinedload(Scan.media))
            .order_by(Scan.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.scalars(stmt)).all())
        return items, total

    async def add_stage(self, scan: Scan, name: str, *, sequence: int) -> ScanStage:
        stage = ScanStage(scan=scan, name=name, status=StageStatus.PENDING, sequence=sequence)
        self.session.add(stage)
        await self.session.flush()
        return stage

    async def set_stage_status(
        self,
        stage: ScanStage,
        *,
        status: StageStatus,
        error: str | None = None,
    ) -> ScanStage:
        now = datetime.now(UTC)
        stage.status = status
        if status is StageStatus.RUNNING and stage.started_at is None:
            stage.started_at = now
        if status in (StageStatus.COMPLETED, StageStatus.FAILED, StageStatus.SKIPPED):
            if stage.started_at is not None and stage.completed_at is None:
                stage.completed_at = now
                stage.duration_ms = int((now - stage.started_at).total_seconds() * 1000)
            elif stage.completed_at is None:
                stage.completed_at = now
                stage.duration_ms = 0
        if error is not None:
            stage.error_message = error
        await self.session.flush()
        return stage

    async def set_status(self, scan: Scan, *, status: ScanStatus) -> Scan:
        scan.status = status
        await self.session.flush()
        return scan
