"""ScanExecutionService: orchestration between worker and pipeline runner.

Given a claimed (PROCESSING) scan, it loads the scan, runs the pipeline, and
finalizes the scan as COMPLETED or FAILED. Owns its own transaction per scan so
cleanup semantics are self-contained.
"""

import logging
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.taxonomy import ScanStatus
from app.media.storage import LocalStorageProvider
from app.repositories.scan import ScanRepository
from app.services.media import SessionFactoryProtocol
from app.services.scans import ScanService
from app.workers.registry import StageRegistry
from app.workers.runner import PipelineFailure, PipelineRunner
from app.workers.stages.base import StageContext

logger = logging.getLogger(__name__)


class ScanExecutionService:
    """Runs one claimed scan through the pipeline to a terminal state."""

    def __init__(
        self,
        *,
        registry: StageRegistry,
        settings: Settings | None = None,
        session_factory: SessionFactoryProtocol | None = None,
    ) -> None:
        self.registry = registry
        self.settings = settings or get_settings()
        self.session_factory = session_factory or SessionFactory
        self.storage = LocalStorageProvider(Path(self.settings.media_storage_root))

    async def execute(self, scan_id: uuid.UUID) -> Scan:
        """Execute one scan; returns the final Scan in a terminal state."""
        async with self.session_factory() as session:
            return await self._execute_in(session, scan_id)

    async def _execute_in(self, session: AsyncSession, scan_id: uuid.UUID) -> Scan:
        scan = await ScanRepository(session).get(scan_id)
        if scan is None:
            raise NotFoundError("scan not found")
        if scan.status is not ScanStatus.PROCESSING:
            raise ConflictError(f"cannot execute scan in state {scan.status.value}")
        scan_service = ScanService(session)
        context = StageContext(
            scan=scan,
            media=scan.media,
            storage=self.storage,
            settings=self.settings,
        )
        runner = PipelineRunner(self.registry)
        try:
            await runner.run(scan, scan_service=scan_service, context=context)
            await scan_service.transition(scan, to=ScanStatus.COMPLETED)
        except PipelineFailure as exc:
            logger.warning("scan %s failed: %s", scan_id, exc.message)
            await scan_service.transition(
                scan, to=ScanStatus.FAILED, error=exc.message
            )
        except Exception:
            logger.exception("scan %s failed unexpectedly", scan_id)
            await scan_service.transition(
                scan, to=ScanStatus.FAILED, error="unexpected pipeline failure"
            )
        await session.commit()
        return scan
