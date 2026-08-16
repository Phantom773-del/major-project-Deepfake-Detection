"""Default XAI explainer registry composition.

Only explainers with real behavior are registered. In this build no detector
model checkpoint exists, so the default registry contains only the honest
``UnavailableExplainer`` — it never fabricates a heatmap. Future explainers
(e.g. a Grad-CAM adapter for a specific detector architecture) register here;
model-specific target-layer assumptions live in those adapters, never in
generic XAI code.
"""

from app.xai.explainers.unavailable import UnavailableExplainer
from app.xai.registry import XAIExplainerRegistry


def build_default_xai_explainer_registry() -> XAIExplainerRegistry:
    """Return the registry of explainers available in this build."""
    registry = XAIExplainerRegistry()
    registry.register(UnavailableExplainer())
    return registry
