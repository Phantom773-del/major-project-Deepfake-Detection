"""Explainable AI (XAI) engine.

The XAI layer produces explanations for genuine detector inference only. With no
detector model in this build, every explanation is UNAVAILABLE with an explicit
reason — never a fabricated heatmap. See ``app/xai/base.py`` for the contract
and the scientific-honesty rules.
"""

from app.xai.explainers import build_default_xai_explainer_registry
from app.xai.registry import XAIExplainerRegistry

__all__ = ["XAIExplainerRegistry", "build_default_xai_explainer_registry"]
