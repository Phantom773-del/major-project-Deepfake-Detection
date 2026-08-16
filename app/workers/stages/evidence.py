"""``evidence`` pipeline stage: aggregate persisted results into one evidence result.

The stage consumes only the structured JSON that prior stages actually persisted
(``ScanStage.result_ref``); it never touches the stored file and never fails just
because one source was unavailable or failed — unavailable and failed sources are
recorded honestly in the availability map.
"""

import json
import logging
from typing import Any

from app.domain.taxonomy import MediaType, StageStatus
from app.evidence import EvidenceAvailability, SourceOutput, aggregate_evidence
from app.evidence.aggregator import SOURCE_BY_STAGE
from app.workers.stages.base import StageContext, StageError, StageResult

logger = logging.getLogger(__name__)


class EvidenceAggregationStage:
    """Aggregates the fingerprint, metadata, detection, forensics, and XAI stages."""

    name = "evidence"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "evidence stage"
            )
        sources: dict[str, SourceOutput] = {
            stage_name: self._source_output(ctx, stage_name)
            for stage_name, _ in SOURCE_BY_STAGE
        }
        result = aggregate_evidence(sources)
        return StageResult(
            result_ref=json.dumps(result.model_dump(mode="json"), sort_keys=True)
        )

    @staticmethod
    def _source_output(ctx: StageContext, name: str) -> SourceOutput:
        stage = next((s for s in ctx.scan.stages if s.name == name), None)
        if stage is None:
            return SourceOutput(
                EvidenceAvailability.UNAVAILABLE, note="stage produced no result"
            )
        if stage.status is StageStatus.FAILED:
            return SourceOutput(EvidenceAvailability.FAILED, note="stage failed")
        if not stage.result_ref:
            return SourceOutput(
                EvidenceAvailability.UNAVAILABLE, note="stage produced no result"
            )
        try:
            payload: Any = json.loads(stage.result_ref)
        except Exception:
            logger.warning(
                "could not parse %s result for scan %s", name, ctx.scan.id
            )
            return SourceOutput(
                EvidenceAvailability.UNAVAILABLE, note="result could not be parsed"
            )
        if not isinstance(payload, dict):
            return SourceOutput(
                EvidenceAvailability.UNAVAILABLE,
                note="result is not a structured payload",
            )
        return SourceOutput(EvidenceAvailability.AVAILABLE, payload=payload)
