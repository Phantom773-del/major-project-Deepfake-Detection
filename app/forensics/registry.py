"""ForensicAnalyzerRegistry: ordered name-to-analyzer mapping.

Mirrors ``StageRegistry``/``DetectorRegistry`` conventions: an analyzer name
registers once, lookups are by name, and ``for_media_type`` returns the
analyzers that serve a media type. No global mutable registry.
"""

from typing import TYPE_CHECKING

from app.domain.taxonomy import MediaType

if TYPE_CHECKING:
    from app.forensics.base import ForensicAnalyzer


class ForensicAnalyzerRegistry:
    """Ordered name-to-analyzer mapping. An analyzer name registers once."""

    def __init__(self) -> None:
        self._analyzers: dict[str, ForensicAnalyzer] = {}

    def register(self, analyzer: ForensicAnalyzer) -> None:
        if analyzer.name in self._analyzers:
            raise ValueError(f"analyzer already registered: {analyzer.name}")
        self._analyzers[analyzer.name] = analyzer

    def get(self, name: str) -> ForensicAnalyzer | None:
        return self._analyzers.get(name)

    def for_media_type(self, media_type: MediaType) -> list[ForensicAnalyzer]:
        """Return analyzers (in registration order) serving ``media_type``."""
        return [
            analyzer
            for analyzer in self._analyzers.values()
            if analyzer.media_type is media_type
        ]

    def names(self) -> list[str]:
        return list(self._analyzers)

    def __contains__(self, name: object) -> bool:
        return name in self._analyzers

    def __len__(self) -> int:
        return len(self._analyzers)
