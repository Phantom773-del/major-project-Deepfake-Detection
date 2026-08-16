"""Risk assessment engine.

Design: risk reflects how concerning/actionable an *established* assessment is
for a reviewer. It is independent of any numeric detector score and never equal
to confidence. Risk cannot be determined without an established directional
assessment, so in this build the engine always returns
``risk_level=UNDETERMINED``.

A non-UNDETERMINED level would require ``confidence_status=SUFFICIENT_EVIDENCE``
from a validated methodology (never emitted in this build) plus directional
evidence; the mapping is documented in docs/BACKEND_IMPLEMENTATION.md §2j and is
deliberately not implemented as code until such a methodology exists — an
arbitrary weight/score formula would fabricate risk.
"""

from app.assessment._evidence import build_references
from app.assessment.domain import ConfidenceResult, RiskLevel, RiskResult
from app.evidence.domain import (
    ConfidenceStatus,
    EvidenceResult,
)

_SEMANTICS = (
    "Risk reflects how concerning/actionable an established assessment is for "
    "review. It is never an authenticity probability, never equal to "
    "confidence, and never derived from a raw detector score. With no "
    "directional assessment established, risk cannot be determined."
)


class RiskEngine:
    """Deterministic, non-fabricating risk assessment."""

    @staticmethod
    def assess(
        evidence: EvidenceResult | None,
        confidence: ConfidenceResult | None,
    ) -> RiskResult:
        references, _by_dimension = build_references(evidence)
        reasons: list[str] = []
        limitations: list[str] = []

        if confidence is None or (
            confidence.confidence_status is not ConfidenceStatus.SUFFICIENT_EVIDENCE
        ):
            reasons.append(
                "confidence is not SUFFICIENT_EVIDENCE; no directional assessment "
                "is established, so risk cannot be determined"
            )
        elif not any(reference.directional for reference in references):
            reasons.append(
                "no directional evidence supports a risk-relevant assessment"
            )
        else:
            reasons.append(
                "risk levels other than UNDETERMINED require a validated "
                "methodology that is not registered in this build"
            )

        if evidence is not None and any(
            reference.source.value == "DETECTION" for reference in references
        ):
            limitations.append(
                "a raw detector score never determines risk; risk depends on an "
                "established assessment, not on a model output"
            )

        return RiskResult(
            risk_level=RiskLevel.UNDETERMINED,
            value=None,
            semantics=_SEMANTICS,
            basis=[r for r in references if r.directional],
            reasons=reasons,
            limitations=limitations,
            methodology_version="1",
        )
