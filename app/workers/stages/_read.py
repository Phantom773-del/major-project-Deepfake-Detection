"""Shared helper for reading a prior stage's persisted result.

Decision stages (confidence, risk, verdict) only consume the structured JSON
that prior stages persisted. A missing, failed or unparseable dependency never
crashes the pipeline — it is read as ``None`` and the decision stages fail
safely toward INSUFFICIENT_EVIDENCE / UNDETERMINED.
"""

import json
import logging
from typing import Any

from app.domain.taxonomy import StageStatus
from app.workers.stages.base import StageContext

logger = logging.getLogger(__name__)


def read_stage_json(ctx: StageContext, name: str) -> dict[str, Any] | None:
    """Return the parsed result payload of a prior stage, or ``None`` when the
    stage produced no readable result."""
    stage = next((s for s in ctx.scan.stages if s.name == name), None)
    if stage is None:
        logger.warning("stage %s produced no result for scan %s", name, ctx.scan.id)
        return None
    if stage.status is StageStatus.FAILED:
        logger.warning("stage %s failed for scan %s", name, ctx.scan.id)
        return None
    if not stage.result_ref:
        logger.warning("stage %s produced no result for scan %s", name, ctx.scan.id)
        return None
    try:
        payload: Any = json.loads(stage.result_ref)
    except Exception:
        logger.warning(
            "could not parse %s result for scan %s", name, ctx.scan.id
        )
        return None
    if not isinstance(payload, dict):
        logger.warning("%s result for scan %s is not a structured payload", name, ctx.scan.id)
        return None
    return payload
