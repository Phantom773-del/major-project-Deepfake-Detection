"""Assessment domain: the confidence, risk and verdict decision layer.

Phase 10 design note (see docs/BACKEND_IMPLEMENTATION.md §2j):

The decision layer consumes the normalized ``EvidenceResult`` produced by the
evidence aggregation stage (Phase 9). It never re-runs analysis, never
invents evidence, and keeps three distinct concepts separate:

- **Confidence** — the strength and consistency of available evidence
  *supporting an assessment*. Never the probability that the media is fake.
- **Risk** — how concerning/actionable an *established* assessment is for a
  reviewer. Independent from confidence; never equal to a detector score.
- **Verdict** — the final defensible conclusion, if any.

No numeric confidence may be emitted in this build: there is no calibrated,
validated methodology, so ``ConfidenceResult.value`` stays ``None`` and
``confidence_status`` stays ``INSUFFICIENT_EVIDENCE``. The shared
``ConfidenceStatus`` enum from ``app.evidence.domain`` is reused — no competing
enum is defined.

Verified evidence, model inference, heuristic interpretation and unknown
signals remain separate (``EvidenceType`` from ``app.domain.taxonomy``).
Unavailable evidence (e.g. no detector model, no XAI, no C2PA provenance) is an
honest state recorded in the availability map — it is never negative evidence
and never elevates risk.
"""

import enum

from pydantic import BaseModel, Field

from app.domain.taxonomy import EvidenceType
from app.evidence.domain import (
    ConfidenceStatus,
    EvidenceCategory,
    EvidenceDirection,
    EvidenceSource,
)


class AssessmentDimension(enum.StrEnum):
    """Which assessment a directional evidence item leans toward.

    ``UNKNOWN`` means the item is a neutral observation that supports no
    assessment. Manipulation and synthetic generation are distinct dimensions:
    editing history never implies synthetic generation.
    """

    AUTHENTIC = "AUTHENTIC"
    MANIPULATED = "MANIPULATED"
    SYNTHETIC = "SYNTHETIC"
    UNKNOWN = "UNKNOWN"


class RiskLevel(enum.StrEnum):
    """How concerning/actionable an established assessment is.

    ``UNDETERMINED`` is the only level emitted in this build: no directional
    assessment exists, so risk cannot be meaningfully established. The
    remaining levels are documented vocabulary for a future validated
    methodology and are never emitted without one.
    """

    UNDETERMINED = "UNDETERMINED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VerdictStatus(enum.StrEnum):
    """Final defensible conclusion for a scan.

    ``INSUFFICIENT_EVIDENCE`` is the only verdict emitted in this build. The
    ``LIKELY_*`` levels require a validated methodology and are never emitted
    without one.
    """

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    INCONCLUSIVE = "INCONCLUSIVE"
    LIKELY_AUTHENTIC = "LIKELY_AUTHENTIC"
    LIKELY_MANIPULATED = "LIKELY_MANIPULATED"
    LIKELY_SYNTHETIC = "LIKELY_SYNTHETIC"


class EvidenceReference(BaseModel):
    """A trimmed reference to one evidence item, used as the basis for a
    decision. Carries the derived assessment classification, which is a
    documented rule mapping — never a verdict."""

    code: str = Field(min_length=1)
    source: EvidenceSource
    category: EvidenceCategory
    evidence_type: EvidenceType
    direction: EvidenceDirection
    correlation_group: str | None = None
    directional: bool
    dimension: AssessmentDimension


class ConfidenceResult(BaseModel):
    """Structured output of the confidence assessment stage (persisted)."""

    status: str = "COMPLETED"
    confidence_status: ConfidenceStatus
    value: float | None = None
    semantics: str = Field(min_length=1)
    basis: list[EvidenceReference] = Field(default_factory=list)
    by_dimension: dict[AssessmentDimension, int] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    methodology_version: str = "1"


class RiskResult(BaseModel):
    """Structured output of the risk assessment stage (persisted)."""

    status: str = "COMPLETED"
    risk_level: RiskLevel
    value: float | None = None
    semantics: str = Field(min_length=1)
    basis: list[EvidenceReference] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    methodology_version: str = "1"


class VerdictResult(BaseModel):
    """Structured output of the final verdict stage (persisted)."""

    status: str = "COMPLETED"
    verdict: VerdictStatus
    semantics: str = Field(min_length=1)
    basis: list[EvidenceReference] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    methodology_version: str = "1"
