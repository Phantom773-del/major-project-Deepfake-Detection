"""DetectorRegistry: ordered name-to-detector mapping.

Mirrors ``StageRegistry`` conventions: a detector name registers once, lookups
are by name, and ``find`` resolves a detector for a media type. The registry is
stateful per construction — no global mutable registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.taxonomy import MediaType

if TYPE_CHECKING:
    from app.inference.base import Detector


class DetectorRegistry:
    """Ordered name-to-detector mapping. A detector name registers once."""

    def __init__(self) -> None:
        self._detectors: dict[str, Detector] = {}

    def register(self, detector: Detector) -> None:
        if detector.name in self._detectors:
            raise ValueError(f"detector already registered: {detector.name}")
        self._detectors[detector.name] = detector

    def get(self, name: str) -> Detector | None:
        return self._detectors.get(name)

    def find(self, media_type: MediaType) -> Detector | None:
        """Return the first registered detector serving ``media_type``."""
        for detector in self._detectors.values():
            if detector.media_type is media_type:
                return detector
        return None

    def names(self) -> list[str]:
        return list(self._detectors)

    def __contains__(self, name: object) -> bool:
        return name in self._detectors

    def __len__(self) -> int:
        return len(self._detectors)
