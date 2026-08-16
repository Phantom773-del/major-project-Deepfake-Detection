"""``forensics`` pipeline stage: measurable visual forensic analysis.

Runs every registered forensic analyzer on the stored image and aggregates their
structured results into the stage ``result_ref``. Analyzer failures are
recorded per-analyzer (status FAILED + error) without aborting the other
analyzers; only image-level failures (unreadable/oversized) fail the stage per
existing pipeline semantics. Runs independently of the ``detect`` stage — a
UNAVAILABLE detector does not block forensics.
"""

import asyncio
import json
import logging
from pathlib import Path

from app.domain.taxonomy import MediaType
from app.forensics.analyzers import build_default_forensic_analyzer_registry
from app.forensics.base import ForensicAnalyzer, ForensicError
from app.forensics.image import validate_image_size
from app.forensics.registry import ForensicAnalyzerRegistry
from app.forensics.result import AnalyzerResult, build_forensic_payload
from app.workers.stages.base import StageContext, StageError, StageResult

logger = logging.getLogger(__name__)


class VisualForensicsStage:
    """Runs all registered analyzers and aggregates their results."""

    name = "forensics"

    def __init__(self, analyzers: ForensicAnalyzerRegistry | None = None) -> None:
        self.analyzers = (
            analyzers if analyzers is not None else build_default_forensic_analyzer_registry()
        )

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "forensics stage"
            )
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except Exception as exc:  # noqa: BLE001 - any resolver failure is client-safe
            raise StageError("invalid storage reference") from exc
        if not path.exists():
            raise StageError("stored media file is missing")
        if len(self.analyzers) == 0:
            raise StageError("no forensic analyzers are configured")
        try:
            image = await asyncio.to_thread(
                validate_image_size, path, max_pixels=ctx.settings.forensics_max_pixels
            )
        except ForensicError as exc:
            raise StageError(exc.message) from exc

        results: list[AnalyzerResult] = []
        for analyzer in self.analyzers.for_media_type(MediaType.IMAGE):
            results.append(
                await asyncio.to_thread(
                    self._run_one, analyzer, path, ctx, name=analyzer.name
                )
            )
        payload = build_forensic_payload(results, image)
        return StageResult(result_ref=json.dumps(payload, sort_keys=True))

    @staticmethod
    def _run_one(
        analyzer: ForensicAnalyzer, path: Path, ctx: StageContext, *, name: str
    ) -> AnalyzerResult:
        """Run one analyzer; never raises, returns a FAILED result on error."""
        try:
            return analyzer.analyze(path, settings=ctx.settings)
        except ForensicError as exc:
            return AnalyzerResult(
                analyzer=name, version="", status="FAILED", error=exc.message
            )
        except Exception:
            logger.exception("forensic analyzer %s failed unexpectedly", name)
            return AnalyzerResult(
                analyzer=name,
                version="",
                status="FAILED",
                error="unexpected analyzer failure",
            )
