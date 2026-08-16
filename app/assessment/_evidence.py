"""Shared basis-building for the assessment engines.

Each decision stage references the evidence items it considered. A
``EvidenceReference`` carries the derived assessment classification produced by
a documented rule mapping — it is a transparent inventory of *what each signal
may lean toward*, never a verdict.
"""

from app.assessment.domain import (
    AssessmentDimension,
    EvidenceReference,
)
from app.evidence.domain import (
    EvidenceAvailability,
    EvidenceDirection,
    EvidenceResult,
)

_DIRECTION_DIMENSION: dict[EvidenceDirection, AssessmentDimension] = {
    EvidenceDirection.SUPPORTING_AUTHENTICITY: AssessmentDimension.AUTHENTIC,
    EvidenceDirection.SUPPORTING_MANIPULATION: AssessmentDimension.MANIPULATED,
    EvidenceDirection.SUPPORTING_EDITING_HISTORY: AssessmentDimension.MANIPULATED,
    EvidenceDirection.SUPPORTING_SYNTHETIC: AssessmentDimension.SYNTHETIC,
    EvidenceDirection.NEUTRAL: AssessmentDimension.UNKNOWN,
    EvidenceDirection.UNKNOWN: AssessmentDimension.UNKNOWN,
}


def _dimension(direction: EvidenceDirection) -> AssessmentDimension:
    return _DIRECTION_DIMENSION.get(direction, AssessmentDimension.UNKNOWN)


def build_references(
    evidence: EvidenceResult | None,
) -> tuple[list[EvidenceReference], dict[AssessmentDimension, int]]:
    """Classify every evidence item into a basis reference list and per-dimension
    directional counts. Returns ``(references, by_dimension)``.

    ``by_dimension`` always contains all four dimensions; AUTHENTIC /
    MANIPULATED / SYNTHETIC count *directional* items, UNKNOWN counts the
    non-directional (neutral) items.
    """
    by_dimension: dict[AssessmentDimension, int] = {
        AssessmentDimension.AUTHENTIC: 0,
        AssessmentDimension.MANIPULATED: 0,
        AssessmentDimension.SYNTHETIC: 0,
        AssessmentDimension.UNKNOWN: 0,
    }
    references: list[EvidenceReference] = []
    if evidence is None:
        return references, by_dimension
    for item in evidence.evidence:
        dimension = _dimension(item.direction)
        directional = dimension is not AssessmentDimension.UNKNOWN
        by_dimension[dimension] += 1
        references.append(
            EvidenceReference(
                code=item.code,
                source=item.source,
                category=item.category,
                evidence_type=item.evidence_type,
                direction=item.direction,
                correlation_group=item.correlation_group,
                directional=directional,
                dimension=dimension,
            )
        )
    return references, by_dimension


def has_unavailable_sources(evidence: EvidenceResult | None) -> bool:
    """Whether any evidence source is unavailable or failed. An unavailable
    source is honest state, never negative evidence."""
    if evidence is None:
        return True
    return any(
        availability is not EvidenceAvailability.AVAILABLE
        for availability in evidence.availability.values()
    )


def has_detector_inference(evidence: EvidenceResult | None) -> bool:
    """Whether a detector model inference item is present at all."""
    if evidence is None:
        return False
    return any(
        item.source.value == "DETECTION" and item.evidence_type.value == "INFERENCE"
        for item in evidence.evidence
    )
