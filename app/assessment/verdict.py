"""Verdict assessment engine.

Design: the verdict is the final defensible conclusion. Manipulation and
synthetic generation are distinct verdicts; editing history never implies
synthetic generation; unavailable evidence is never evidence. In this build no
directional assessment can be established, so the engine always returns
``verdict=INSUFFICIENT_EVIDENCE``.

``INCONCLUSIVE`` is reserved for a future scan with directional evidence that
does not converge on a single assessment. ``LIKELY_AUTHENTIC`` /
``LIKELY_MANIPULATED`` / ``LIKELY_SYNTHETIC`` require a validated methodology
(docs/BACKEND_IMPLEMENTATION.md §2j) and are never emitted without one.
"""

from app.assessment._evidence import build_references
from app.assessment.domain import ConfidenceResult, VerdictResult, VerdictStatus
from app.evidence.domain import (
    ConfidenceStatus,
    EvidenceResult,
)

_SEMANTICS = (
    "The verdict is the final defensible conclusion of the pipeline. It is "
    "never stronger than the evidence: without a validated methodology and a "
    "directional assessment, the honest verdict is INSUFFICIENT_EVIDENCE."
)


class VerdictEngine:
    """Deterministic, non-fabricating verdict assessment."""

    @staticmethod
    def reach(
        evidence: EvidenceResult | None,
        confidence: ConfidenceResult | None,
    ) -> VerdictResult:
        references, _by_dimension = build_references(evidence)
        reasons: list[str] = []
        limitations: list[str] = []

        if confidence is None or (
            confidence.confidence_status is not ConfidenceStatus.SUFFICIENT_EVIDENCE
        ):
            verdict = VerdictStatus.INSUFFICIENT_EVIDENCE
            reasons.append(
                "confidence is not SUFFICIENT_EVIDENCE; no defensible conclusion "
                "can be reached"
            )
        elif not any(reference.directional for reference in references):
            verdict = VerdictStatus.INSUFFICIENT_EVIDENCE
            reasons.append(
                "no directional evidence supports any assessment conclusion"
            )
        else:
            verdict = VerdictStatus.INSUFFICIENT_EVIDENCE
            reasons.append(
                "verdict levels other than INSUFFICIENT_EVIDENCE require a "
                "validated methodology that is not registered in this build; "
                "manipulation and synthetic generation are kept distinct"
            )

        if evidence is not None and any(
            reference.source.value == "DETECTION" for reference in references
        ):
            limitations.append(
                "a detector score alone never produces a verdict; it is a model "
                "output, not a validated conclusion"
            )

        return VerdictResult(
            verdict=verdict,
            semantics=_SEMANTICS,
            basis=references,
            reasons=reasons,
            limitations=limitations,
            methodology_version="1",
        )
