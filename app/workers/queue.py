"""In-process analysis worker (v1).

The worker answers "which queued scan should execute?". It claims one QUEUED
scan per iteration using a database row lock (``FOR UPDATE SKIP LOCKED``), so
even multiple worker processes would never process the same scan twice. It then
hands the claimed scan to the execution service, which runs the pipeline.

Scope: single-process scheduling loop, no Celery/Redis. Distributed retries and
horizontal worker coordination are out of scope and documented as a limitation.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.config import Settings, get_settings
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.taxonomy import ScanStatus
from app.services.execution import ScanExecutionService
from app.services.media import SessionFactoryProtocol
from app.services.scans import ScanService
from app.workers.stages import build_default_registry

logger = logging.getLogger(__name__)


class AnalysisWorker:
    """Claims queued scans and drives them to a terminal state."""

    def __init__(
        self,
        *,
        session_factory: SessionFactoryProtocol,
        execution: ScanExecutionService,
        poll_interval: float,
    ) -> None:
        self.session_factory = session_factory
        self.execution = execution
        self.poll_interval = poll_interval

    async def run_once(self) -> int:
        """Claim and execute at most one scan. Returns 1 if work was done."""
        async with self.session_factory() as session:
            scan = await self._claim_next(session)
        if scan is None:
            return 0
        await self.execution.execute(scan.id)
        return 1

    async def run_until_idle(self) -> int:
        """Process queued scans until the queue is empty. Returns work count."""
        total = 0
        while await self.run_once():
            total += 1
        return total

    async def run_forever(self) -> None:
        """Continuous polling loop for the background worker task."""
        while True:
            try:
                if await self.run_once() == 0:
                    await asyncio.sleep(self.poll_interval)
            except Exception:
                logger.exception("worker iteration failed")
                await asyncio.sleep(self.poll_interval)

    async def _claim_next(self, session: AsyncSession) -> Scan | None:
        """Atomically claim the oldest QUEUED scan, moving it to PROCESSING."""
        stmt = (
            select(Scan)
            .options(joinedload(Scan.media), selectinload(Scan.stages))
            .where(Scan.status == ScanStatus.QUEUED)
            .order_by(Scan.created_at.asc())
            .limit(1)
            .with_for_update(of=Scan, skip_locked=True)
        )
        scan = await session.scalar(stmt)
        if scan is None:
            return None
        await ScanService(session).transition(scan, to=ScanStatus.PROCESSING)
        await session.commit()
        return scan


def build_default_worker(settings: Settings | None = None) -> AnalysisWorker:
    """Compose the default worker from the registry, settings and session factory."""
    settings = settings or get_settings()
    execution = ScanExecutionService(
        registry=build_default_registry(),
        settings=settings,
        session_factory=SessionFactory,
    )
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=settings.analysis_worker_poll_interval_seconds,
    )
