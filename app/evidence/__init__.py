"""Evidence aggregation engine (Phase 9).

Normalizes the persisted outputs of the fingerprint, metadata, detection,
visual forensics, and XAI stages into one deterministic evidence result. The
engine only consumes structured results the pipeline actually persisted; it
never invents evidence, never turns UNAVAILABLE into a negative signal, and
never emits a numeric confidence it cannot defend.
"""

from app.evidence.aggregator import SourceOutput, aggregate_evidence
from app.evidence.domain import (
    ConfidenceAssessment,
    ConfidenceStatus,
    CorrelationNote,
    EvidenceAvailability,
    EvidenceCategory,
    EvidenceDirection,
    EvidenceItem,
    EvidenceMethodology,
    EvidenceResult,
    EvidenceSource,
    EvidenceSummary,
)
from app.evidence.normalizer import normalize_source

__all__ = [
    "ConfidenceAssessment",
    "ConfidenceStatus",
    "CorrelationNote",
    "EvidenceAvailability",
    "EvidenceCategory",
    "EvidenceDirection",
    "EvidenceItem",
    "EvidenceMethodology",
    "EvidenceResult",
    "EvidenceSource",
    "EvidenceSummary",
    "SourceOutput",
    "aggregate_evidence",
    "normalize_source",
]
