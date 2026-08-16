"""Explicit unavailable-detector state.

No PHANTOM PHOENIX detector checkpoint exists in this build (the Phase 1
EfficientNet-B4 model was never committed — no weights, no inference code).
``UnavailableDetector`` is the honest placeholder: it always reports
``UNAVAILABLE`` with no prediction, so the pipeline never fabricates detection
results.
"""

from pathlib import Path

from app.domain.taxonomy import MediaType
from app.inference.base import (
    DetectionResult,
    DetectorIdentity,
    InferenceSummary,
)


class UnavailableDetector:
    """Always-available placeholder that produces no prediction."""

    name = "unavailable"
    media_type = MediaType.IMAGE

    @property
    def identity(self) -> DetectorIdentity:
        return DetectorIdentity(
            name=self.name,
            model_name=None,
            model_version=None,
            checkpoint_sha256=None,
            preprocessing_version=None,
        )

    def detect(self, path: Path, *, device: str) -> DetectionResult:
        return DetectionResult(
            detector=self.identity,
            media_type=self.media_type,
            prediction=None,
            inference=InferenceSummary(
                status="UNAVAILABLE",
                reason="no image detector is registered in this build",
                device=device,
            ),
            evidence_type=None,
        )
