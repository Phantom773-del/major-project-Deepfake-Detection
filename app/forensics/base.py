"""Forensic analyzer abstraction.

A forensic analyzer performs ONE measurable image-level computation and returns
a structured ``AnalyzerResult``. Analyzers never write to the database, never
decide REAL/FAKE/AI-GENERATED/MANIPULATED, and never emit an authenticity
probability. Measurements are observations; interpretations are HEURISTIC
supporting evidence only.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from app.core.config import Settings
from app.domain.taxonomy import MediaType

if TYPE_CHECKING:
    from app.forensics.result import AnalyzerResult


class ForensicError(Exception):
    """Client-safe failure raised by a forensic analyzer or image loader.

    ``message`` contains no paths, tracebacks, or internals.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ForensicAnalyzer(Protocol):
    """One independently-testable visual forensic computation."""

    name: str
    media_type: MediaType
    version: str

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        """Run the analysis on a resolved media path.

        Raise ``ForensicError`` on failure. Must be deterministic for identical
        input bytes and settings.
        """
        ...
