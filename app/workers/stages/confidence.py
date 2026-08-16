"""``confidence`` pipeline stage: assess confidence from the evidence result.

The stage consumes the persisted evidence aggregation result (``ScanStage
result_ref``), never re-runs analysis. If the evidence result is missing or
unparseable the stage fails safely toward INSUFFICIENT_EVIDENCE.
"""

import json

from app.assessment import ConfidenceEngine
from app.domain.taxonomy import MediaType
from app.evidence.domain import EvidenceResult
from app.workers.stages._read import read_stage_json
from app.workers.stages.base import StageContext, StageError, StageResult


class ConfidenceStage:
    """Deterministic confidence assessment over the evidence result."""

    name = "confidence"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "confidence stage"
            )
        payload = read_stage_json(ctx, "evidence")
        evidence: EvidenceResult | None = None
        if payload is not None:
            evidence = EvidenceResult.model_validate(payload)
        result = ConfidenceEngine.assess(evidence)
        return StageResult(
            result_ref=json.dumps(result.model_dump(mode="json"), sort_keys=True)
        )
