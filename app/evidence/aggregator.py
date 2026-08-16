"""Deterministic aggregation of normalized evidence into one result.

The aggregator combines per-source ``SourceOutput`` in pipeline order, never
fails on an unavailable or failed source, deduplicates correlated signals
(only the first item of a correlation group counts toward ``independent_count``),
and emits a confidence assessment that is honest about the absence of a
validated probability model.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from app.evidence.domain import (
    ConfidenceAssessment,
    ConfidenceStatus,
    CorrelationNote,
    EvidenceAvailability,
    EvidenceItem,
    EvidenceMethodology,
    EvidenceResult,
    EvidenceSource,
    EvidenceSummary,
)
from app.evidence.normalizer import CORRELATION_NOTE, normalize_source

# Source stages in pipeline order, mapped to their evidence source.
SOURCE_BY_STAGE: tuple[tuple[str, EvidenceSource], ...] = (
    ("fingerprint", EvidenceSource.FINGERPRINT),
    ("metadata", EvidenceSource.METADATA),
    ("detect", EvidenceSource.DETECTION),
    ("forensics", EvidenceSource.VISUAL_FORENSICS),
    ("xai", EvidenceSource.XAI),
)

_CONFIDENCE_SEMANTICS = (
    "Confidence reflects the strength and consistency of available evidence "
    "supporting an assessment, not the probability that the media is fake."
)

_CONFIDENCE_BASE_REASONS: tuple[str, ...] = (
    "no calibrated probability model exists in this build; a numeric confidence "
    "would be fabricated, not computed",
    "sufficiency is reported, never a probability",
)


@dataclass(frozen=True)
class SourceOutput:
    """What the evidence stage knows about one source stage before aggregation.

    ``payload`` is the persisted structured result when the source stage
    completed with usable output; otherwise ``availability`` and ``note``
    describe the honest state.
    """

    availability: EvidenceAvailability
    payload: dict[str, Any] | None = None
    note: str | None = None


def aggregate_evidence(sources: Mapping[str, SourceOutput]) -> EvidenceResult:
    """Build the deterministic evidence result for one scan."""
    items: list[EvidenceItem] = []
    availability: dict[EvidenceSource, EvidenceAvailability] = {}
    limitations: list[str] = []

    for stage_name, source in SOURCE_BY_STAGE:
        output = sources.get(stage_name)
        if output is None or output.payload is None:
            availability[source] = (
                output.availability if output is not None else EvidenceAvailability.UNAVAILABLE
            )
            note = output.note if output is not None else "stage produced no result"
            limitations.append(
                f"{source.value} evidence is {availability[source].value.lower()}: {note}"
            )
            continue
        normalized = normalize_source(source, output.payload)
        availability[source] = normalized.availability
        items.extend(normalized.items)
        for limitation in normalized.limitations:
            limitations.append(f"{source.value}: {limitation}")

    items.sort(key=lambda item: (item.source.value, item.code))
    return EvidenceResult(
        methodology=EvidenceMethodology(),
        availability=availability,
        evidence=items,
        summary=_build_summary(items),
        correlation=_build_correlation(items),
        confidence=_build_confidence(availability),
        limitations=limitations,
    )


def _build_summary(items: list[EvidenceItem]) -> EvidenceSummary:
    return EvidenceSummary(
        total=len(items),
        independent_count=len(_independent_items(items)),
        by_evidence_type=_sorted_counts(item.evidence_type for item in items),
        by_direction=_sorted_counts(item.direction for item in items),
        by_category=_sorted_counts(item.category for item in items),
    )


def _independent_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    """Items that are not duplicates of a correlated signal group.

    Within a correlation group only the first item counts as independent
    (e.g. XAI is never treated as independent detector evidence).
    """
    seen: set[str] = set()
    independent: list[EvidenceItem] = []
    for item in items:
        if item.correlation_group is not None:
            if item.correlation_group in seen:
                continue
            seen.add(item.correlation_group)
        independent.append(item)
    return independent


def _sorted_counts(values: Iterable[object]) -> dict[str, int]:
    counter: Counter[str] = Counter(str(value) for value in values)
    return {key: counter[key] for key in sorted(counter)}


def _build_correlation(items: list[EvidenceItem]) -> CorrelationNote:
    groups = sorted(
        {item.correlation_group for item in items if item.correlation_group is not None}
    )
    return CorrelationNote(groups=groups, note=CORRELATION_NOTE)


def _build_confidence(
    availability: Mapping[EvidenceSource, EvidenceAvailability],
) -> ConfidenceAssessment:
    reasons = list(_CONFIDENCE_BASE_REASONS)
    for source in sorted(availability, key=lambda source: source.value):
        if availability[source] is not EvidenceAvailability.AVAILABLE:
            reasons.append(f"{source.value} evidence is {availability[source].value.lower()}")
    return ConfidenceAssessment(
        status=ConfidenceStatus.INSUFFICIENT_EVIDENCE,
        value=None,
        semantics=_CONFIDENCE_SEMANTICS,
        reasons=reasons,
    )
