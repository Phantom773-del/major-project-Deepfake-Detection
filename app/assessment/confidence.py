"""Confidence assessment engine.

Design: confidence is *the strength and consistency of available evidence
supporting an assessment*, never the probability that the media is fake. No
calibrated, validated methodology exists in this build, so the engine can never
emit a numeric value or a stronger qualitative level: it always returns
``confidence_status=INSUFFICIENT_EVIDENCE`` with ``value=None``, a full evidence
basis with the derived directional classification, and honest limitations.

The conditions a *future* methodology must meet before ``SUFFICIENT_EVIDENCE``
may be emitted are documented in docs/BACKEND_IMPLEMENTATION.md §2j. A detector
model score is a model output with its own ``score_semantics`` — it is never
interpreted here as a calibrated probability.
"""

from app.assessment._evidence import (
    build_references,
    has_detector_inference,
    has_unavailable_sources,
)
from app.assessment.domain import ConfidenceResult
from app.evidence.domain import (
    ConfidenceStatus,
    EvidenceResult,
)

_SEMANTICS = (
    "Confidence reflects the strength and consistency of available evidence "
    "supporting an assessment — never the probability that the media is fake. "
    "In this build no validated, calibrated methodology is registered, so "
    "confidence is INSUFFICIENT_EVIDENCE and carries no numeric value."
)


class ConfidenceEngine:
    """Deterministic, non-fabricating confidence assessment."""

    @staticmethod
    def assess(evidence: EvidenceResult | None) -> ConfidenceResult:
        references, by_dimension = build_references(evidence)
        reasons: list[str] = []
        limitations: list[str] = []

        if evidence is None:
            reasons.append("the evidence stage produced no readable result")
            return ConfidenceResult(
                confidence_status=ConfidenceStatus.INSUFFICIENT_EVIDENCE,
                value=None,
                semantics=_SEMANTICS,
                basis=references,
                by_dimension=by_dimension,
                reasons=reasons,
                limitations=[
                    "no evidence was available for the confidence assessment"
                ],
                methodology_version="1",
            )

        directional = [reference for reference in references if reference.directional]
        if not evidence.evidence:
            reasons.append("no evidence items were produced")
        elif not directional:
            reasons.append(
                "all evidence items are neutral observations; none supports any "
                "assessment direction"
            )
        else:
            counts = {k: v for k, v in by_dimension.items() if k.value != "UNKNOWN"}
            reasons.append(
                "directional evidence exists but no validated methodology is "
                f"registered to interpret it; inventory: {counts}"
            )

        if has_detector_inference(evidence):
            limitations.append(
                "a detector model score is present but is not a calibrated "
                "probability; no validated methodology exists to interpret it "
                "as one, so it cannot raise confidence"
            )
        if has_unavailable_sources(evidence):
            for source, availability in evidence.availability.items():
                if availability.value != "AVAILABLE":
                    limitations.append(
                        f"{source.value} evidence is {availability.value.lower()}; "
                        "absence is not negative evidence and cannot reduce "
                        "confidence"
                    )
        reasons.append(
            "no calibrated confidence methodology is registered in this build; "
            "numeric and qualitative confidence levels are not emitted"
        )
        reasons.append(
            f"evidence methodology version {evidence.methodology.version}; "
            f"correlation groups considered: {evidence.correlation.groups}"
        )

        return ConfidenceResult(
            confidence_status=ConfidenceStatus.INSUFFICIENT_EVIDENCE,
            value=None,
            semantics=_SEMANTICS,
            basis=references,
            by_dimension=by_dimension,
            reasons=reasons,
            limitations=limitations,
            methodology_version="1",
        )
