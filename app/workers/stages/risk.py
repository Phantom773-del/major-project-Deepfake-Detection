"""``risk`` pipeline stage: assess risk from the evidence and confidence results.

Consumes only persisted results; never re-runs analysis. Missing dependencies
fail safely toward UNDETERMINED — a raw detector score never determines risk.
"""

import json

from app.assessment import ConfidenceResult, RiskEngine
from app.domain.taxonomy import MediaType
from app.evidence.domain import EvidenceResult
from app.workers.stages._read import read_stage_json
from app.workers.stages.base import StageContext, StageError, StageResult


class RiskStage:
    """Deterministic risk assessment over the evidence and confidence results."""

    name = "risk"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "risk stage"
            )
        evidence: EvidenceResult | None = None
        confidence: ConfidenceResult | None = None
        evidence_payload = read_stage_json(ctx, "evidence")
        if evidence_payload is not None:
            evidence = EvidenceResult.model_validate(evidence_payload)
        confidence_payload = read_stage_json(ctx, "confidence")
        if confidence_payload is not None:
            confidence = ConfidenceResult.model_validate(confidence_payload)
        result = RiskEngine.assess(evidence, confidence)
        return StageResult(
            result_ref=json.dumps(result.model_dump(mode="json"), sort_keys=True)
        )
