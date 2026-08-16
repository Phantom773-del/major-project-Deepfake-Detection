"""Default forensic analyzer composition.

The default registry ships the three implemented analyzers (ELA, noise
residual, frequency). Future analyzers (texture, JPEG ghosts, etc.) register
here without touching the pipeline.
"""

from app.forensics.analyzers.ela import ErrorLevelAnalyzer
from app.forensics.analyzers.frequency import FrequencyAnalyzer
from app.forensics.analyzers.noise import NoiseResidualAnalyzer
from app.forensics.registry import ForensicAnalyzerRegistry


def build_default_forensic_analyzer_registry() -> ForensicAnalyzerRegistry:
    """Return the registry of analyzers available in this build."""
    registry = ForensicAnalyzerRegistry()
    registry.register(ErrorLevelAnalyzer())
    registry.register(NoiseResidualAnalyzer())
    registry.register(FrequencyAnalyzer())
    return registry
