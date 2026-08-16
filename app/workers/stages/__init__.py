"""Default pipeline stage registry.

Only stages with real behavior are registered here. Names come from
``STAGE_ORDER`` in ``app/domain/scan.py``; stages not registered are marked
SKIPPED by the runner with an explicit "not implemented in this build" reason —
they are never faked.
"""

from app.workers.registry import StageRegistry
from app.workers.stages.confidence import ConfidenceStage
from app.workers.stages.detect import DetectionStage
from app.workers.stages.evidence import EvidenceAggregationStage
from app.workers.stages.fingerprint import FingerprintStage
from app.workers.stages.forensics import VisualForensicsStage
from app.workers.stages.metadata import MetadataStage
from app.workers.stages.report import ReportStage
from app.workers.stages.risk import RiskStage
from app.workers.stages.validate import ValidateStage
from app.workers.stages.verdict import VerdictStage
from app.workers.stages.xai import XAIStage


def build_default_registry() -> StageRegistry:
    """Return the registry of stages implemented in this build."""
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(DetectionStage())
    registry.register(VisualForensicsStage())
    registry.register(XAIStage())
    registry.register(EvidenceAggregationStage())
    registry.register(ConfidenceStage())
    registry.register(RiskStage())
    registry.register(VerdictStage())
    registry.register(ReportStage())
    return registry
