"""Default detector registry composition.

Only detectors with real behavior are registered. In this build no model
checkpoint is available, so the default registry contains only the honest
``UnavailableDetector`` (never fabricates a prediction). Future image/video
detectors register here.
"""

from app.inference.detectors.unavailable import UnavailableDetector
from app.inference.registry import DetectorRegistry


def build_default_detector_registry() -> DetectorRegistry:
    """Return the registry of detectors available in this build."""
    registry = DetectorRegistry()
    registry.register(UnavailableDetector())
    return registry
