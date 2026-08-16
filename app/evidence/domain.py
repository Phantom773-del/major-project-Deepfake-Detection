"""Evidence domain: the normalized evidence model shared across the pipeline.

The engine reuses the shared ``EvidenceType`` taxonomy (VERIFIED / INFERENCE /
HEURISTIC / UNKNOWN) from ``app.domain.taxonomy`` — it never defines a competing
classification. Each evidence item is a single observation normalized from a
real stage result; a *direction* only ever records what a signal *may support*,
never a verdict.

Confidence semantics (Phase 9 design note):
- ``ConfidenceAssessment.value`` is the raw numeric value a *validated*
  methodology could produce. In this build no calibrated probability model
  exists, so the aggregator always emits ``status=INSUFFICIENT_EVIDENCE`` and
  ``value=None`` — a numeric confidence would be fabricated, not computed.
- "Confidence" means *the strength and consistency of available evidence
  supporting an assessment*, never the probability that the media is fake.
"""

import enum

from pydantic import BaseModel, Field

from app.domain.taxonomy import EvidenceType


class EvidenceSource(enum.StrEnum):
    """Which pipeline stage produced an evidence item."""

    FINGERPRINT = "FINGERPRINT"
    METADATA = "METADATA"
    DETECTION = "DETECTION"
    VISUAL_FORENSICS = "VISUAL_FORENSICS"
    XAI = "XAI"


class EvidenceCategory(enum.StrEnum):
    """What kind of claim an evidence item supports.

    Only categories backed by an implemented source are included. There is no
    MANIPULATION category: no implemented source produces evidence that supports
    a manipulation claim.
    """

    FILE_INTEGRITY = "FILE_INTEGRITY"
    PROVENANCE = "PROVENANCE"
    METADATA_CONSISTENCY = "METADATA_CONSISTENCY"
    VISUAL_ANOMALY = "VISUAL_ANOMALY"
    MODEL_BEHAVIOR = "MODEL_BEHAVIOR"
    SYNTHETIC_GENERATION = "SYNTHETIC_GENERATION"
    AUTHENTICITY = "AUTHENTICITY"


class EvidenceDirection(enum.StrEnum):
    """What a signal may tentatively support (never a verdict).

    ``UNKNOWN`` means the item has no interpretable direction; ``NEUTRAL`` means
    it is a plain observation that supports no assessment either way.
    """

    UNKNOWN = "UNKNOWN"
    NEUTRAL = "NEUTRAL"
    SUPPORTING_AUTHENTICITY = "SUPPORTING_AUTHENTICITY"
    SUPPORTING_MANIPULATION = "SUPPORTING_MANIPULATION"
    SUPPORTING_SYNTHETIC = "SUPPORTING_SYNTHETIC"
    SUPPORTING_EDITING_HISTORY = "SUPPORTING_EDITING_HISTORY"


class EvidenceAvailability(enum.StrEnum):
    """Whether a source contributed usable evidence to this scan.

    ``UNAVAILABLE`` is an honest state (no negative evidence), and a source that
    produced no evidence is never treated as evidence against authenticity.
    """

    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class ConfidenceStatus(enum.StrEnum):
    """Sufficiency of evidence for a directional assessment.

    ``SUFFICIENT_EVIDENCE`` is reserved for a future validated methodology; the
    aggregator never emits it in this build.
    """

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"


class EvidenceItem(BaseModel):
    """One normalized observation with its classification and direction."""

    code: str = Field(min_length=1)
    source: EvidenceSource
    category: EvidenceCategory
    evidence_type: EvidenceType
    observation: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    direction: EvidenceDirection = EvidenceDirection.NEUTRAL
    correlation_group: str | None = None
    details: dict[str, object] | None = None


class EvidenceSummary(BaseModel):
    """Aggregate counts over the normalized evidence items."""

    total: int = 0
    independent_count: int = 0
    by_evidence_type: dict[str, int] = Field(default_factory=dict)
    by_direction: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)


class CorrelationNote(BaseModel):
    """Which correlated signal groups are present and how they were handled."""

    groups: list[str] = Field(default_factory=list)
    note: str = ""


class ConfidenceAssessment(BaseModel):
    """Honest confidence statement for this scan's available evidence."""

    status: ConfidenceStatus
    value: float | None = None
    semantics: str = Field(min_length=1)
    reasons: list[str] = Field(default_factory=list)


class EvidenceMethodology(BaseModel):
    """Version and rules used to build this evidence result."""

    version: str = "1"
    aggregation: str = "evidence-count"
    correlation: str = "dedupe-by-group"
    confidence: str = "sufficiency-based; non-numeric"


class EvidenceResult(BaseModel):
    """Structured output of the evidence aggregation stage (persisted)."""

    status: str = "COMPLETED"
    methodology: EvidenceMethodology = Field(default_factory=EvidenceMethodology)
    availability: dict[EvidenceSource, EvidenceAvailability] = Field(
        default_factory=dict
    )
    evidence: list[EvidenceItem] = Field(default_factory=list)
    summary: EvidenceSummary = Field(default_factory=EvidenceSummary)
    correlation: CorrelationNote = Field(default_factory=CorrelationNote)
    confidence: ConfidenceAssessment
    limitations: list[str] = Field(default_factory=list)
