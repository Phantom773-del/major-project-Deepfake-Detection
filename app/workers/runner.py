"""PipelineRunner and StageRegistry.

The runner answers "how does the analysis pipeline execute?": it walks the
canonical ``STAGE_ORDER`` and either runs a registered stage or marks the stage
SKIPPED with an explicit reason. It never invents results for stages without
implementations.
"""

import logging

from app.db.models.scan import Scan
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import StageStatus
from app.services.scans import ScanService
from app.workers.registry import StageRegistry
from app.workers.stages.base import StageContext, StageError

logger = logging.getLogger(__name__)

NOT_IMPLEMENTED_REASON = "not implemented in this build"


class PipelineFailure(Exception):
    """Scan-level pipeline failure; ``message`` is client-safe."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class PipelineRunner:
    """Executes registered stages in canonical order for one scan."""

    def __init__(self, registry: StageRegistry) -> None:
        self.registry = registry

    async def run(
        self,
        scan: Scan,
        *,
        scan_service: ScanService,
        context: StageContext,
    ) -> None:
        for name in STAGE_ORDER:
            stage = self.registry.get(name)
            if stage is None:
                await scan_service.mark_stage(
                    scan,
                    name=name,
                    status=StageStatus.SKIPPED,
                    error=f"{name!r} stage {NOT_IMPLEMENTED_REASON}",
                )
                continue
            await scan_service.mark_stage(
                scan, name=name, status=StageStatus.RUNNING
            )
            try:
                result = await stage.run(context)
            except StageError as exc:
                logger.warning(
                    "stage %s failed for scan %s: %s", name, scan.id, exc.message
                )
                await scan_service.mark_stage(
                    scan, name=name, status=StageStatus.FAILED, error=exc.message
                )
                raise PipelineFailure(exc.message) from exc
            except Exception as exc:
                logger.exception("stage %s raised unexpectedly for scan %s", name, scan.id)
                await scan_service.mark_stage(
                    scan,
                    name=name,
                    status=StageStatus.FAILED,
                    error="unexpected stage failure",
                )
                raise PipelineFailure("unexpected stage failure") from exc
            await scan_service.mark_stage(
                scan,
                name=name,
                status=StageStatus.COMPLETED,
                result_ref=result.result_ref if result is not None else None,
            )
