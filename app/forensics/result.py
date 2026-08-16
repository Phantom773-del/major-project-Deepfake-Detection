"""Structured forensic result payloads.

Findings carry the shared ``EvidenceType`` taxonomy: a measurement statement is
``VERIFIED`` (directly computed), an interpretation is ``HEURISTIC`` (supporting
signal only). No finding ever claims proof of AI generation or manipulation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from app.domain.taxonomy import EvidenceType
from app.forensics.image import ImageInfo

# Float values are rounded to this many decimal places in the payload so output
# stays compact and stable across platforms.
_DECIMAL_PLACES = 6

AnalyzerStatus = Literal["COMPLETED", "FAILED"]


class ForensicFinding:
    """A classified statement about a forensic measurement."""

    __slots__ = ("code", "evidence_type", "message")

    def __init__(self, code: str, evidence_type: EvidenceType, message: str) -> None:
        self.code = code
        self.evidence_type = evidence_type
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "evidence_type": self.evidence_type.value,
            "message": self.message,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ForensicFinding):
            return NotImplemented
        return (
            self.code == other.code
            and self.evidence_type is other.evidence_type
            and self.message == other.message
        )

    def __hash__(self) -> int:
        return hash((self.code, self.evidence_type, self.message))


class AnalyzerResult:
    """Output of one analyzer run: measurements + classified findings."""

    __slots__ = (
        "analyzer",
        "version",
        "status",
        "measurements",
        "parameters",
        "findings",
        "error",
    )

    def __init__(
        self,
        *,
        analyzer: str,
        version: str,
        status: AnalyzerStatus,
        measurements: Mapping[str, int | float] | None = None,
        parameters: Mapping[str, int | float] | None = None,
        findings: Sequence[ForensicFinding] = (),
        error: str | None = None,
    ) -> None:
        self.analyzer = analyzer
        self.version = version
        self.status = status
        self.measurements = dict(measurements or {})
        self.parameters = dict(parameters or {})
        self.findings = tuple(findings)
        self.error = error


def build_forensic_payload(
    results: Sequence[AnalyzerResult], image: ImageInfo
) -> dict[str, object]:
    """Return the deterministic JSON-serializable forensics stage payload."""
    analyzers: dict[str, object] = {}
    completed = 0
    failed = 0
    for result in results:
        analyzers[result.analyzer] = _analyzer_dict(result)
        if result.status == "COMPLETED":
            completed += 1
        else:
            failed += 1
    return {
        "image": {
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
        },
        "summary": {
            "analyzers": len(results),
            "completed": completed,
            "failed": failed,
        },
        "analyzers": analyzers,
    }


def _analyzer_dict(result: AnalyzerResult) -> dict[str, object]:
    return {
        "analyzer": result.analyzer,
        "version": result.version,
        "status": result.status,
        "error": result.error,
        "parameters": _round_mapping(result.parameters),
        "measurements": _round_mapping(result.measurements),
        "findings": [f.as_dict() for f in result.findings],
    }


def _round_mapping(values: Mapping[str, object]) -> dict[str, object]:
    return {key: _round(value) for key, value in values.items()}


def _round(value: object) -> object:
    if isinstance(value, float):
        return round(value, _DECIMAL_PLACES)
    return value
