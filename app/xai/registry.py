"""XAIExplainerRegistry: ordered name-to-explainer mapping.

Mirrors ``DetectorRegistry`` conventions: an explainer name registers once,
lookups are by name, and ``find`` resolves an explainer for a media type and a
specific detector model. ``find`` prefers an explainer that names the exact
model, then falls back to a ``model_type=None`` explainer (the honest
unavailable fallback) — so the registry is never left with a silent hole.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.taxonomy import MediaType

if TYPE_CHECKING:
    from app.xai.base import XAIExplainer


class XAIExplainerRegistry:
    """Ordered name-to-explainer mapping. An explainer name registers once."""

    def __init__(self) -> None:
        self._explainers: dict[str, XAIExplainer] = {}

    def register(self, explainer: XAIExplainer) -> None:
        if explainer.name in self._explainers:
            raise ValueError(f"explainer already registered: {explainer.name}")
        self._explainers[explainer.name] = explainer

    def get(self, name: str) -> XAIExplainer | None:
        return self._explainers.get(name)

    def find(
        self, media_type: MediaType, model_type: str | None
    ) -> XAIExplainer | None:
        """Resolve an explainer for a media type and detector model.

        Exact ``model_type`` matches win; otherwise the first ``model_type=None``
        explainer (the unavailable fallback) is returned.
        """
        for explainer in self._explainers.values():
            if (
                explainer.media_type is media_type
                and explainer.model_type == model_type
            ):
                return explainer
        for explainer in self._explainers.values():
            if explainer.media_type is media_type and explainer.model_type is None:
                return explainer
        return None

    def names(self) -> list[str]:
        return list(self._explainers)

    def __contains__(self, name: object) -> bool:
        return name in self._explainers

    def __len__(self) -> int:
        return len(self._explainers)
