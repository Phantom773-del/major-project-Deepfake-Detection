"""forensics package: measurable visual forensic analysis.

Each analyzer produces a structured, deterministic ``AnalyzerResult``
(measurements + evidence-classified findings). Measurements are observations,
never authenticity verdicts.
"""

from app.forensics.analyzers import build_default_forensic_analyzer_registry
from app.forensics.base import ForensicAnalyzer, ForensicError
from app.forensics.registry import ForensicAnalyzerRegistry

__all__ = [
    "ForensicAnalyzer",
    "ForensicAnalyzerRegistry",
    "ForensicError",
    "build_default_forensic_analyzer_registry",
]
