"""Explicit unavailable-XAI state.

No PHANTOM PHOENIX detector checkpoint exists in this build (see
``app/inference/detectors/unavailable.py``), so there is no differentiable model
to explain and no real activation map can exist. ``UnavailableExplainer`` is the
honest fallback: it always reports ``UNAVAILABLE`` with a clear reason and never
produces a heatmap, a score, or an interpretation. It is NOT a placeholder that
pretends to run Grad-CAM — it reports the real system state.
"""

from pathlib import Path

from app.core.config import Settings
from app.domain.taxonomy import MediaType
from app.xai.base import (
    ExplainerIdentity,
    XAIExplanationContext,
    XAIModelIdentity,
    XAIResult,
)


class UnavailableExplainer:
    """Always-available fallback that produces no explanation."""

    name = "unavailable"
    version = "1"
    technique = "none"
    media_type = MediaType.IMAGE
    model_type: str | None = None

    @property
    def identity(self) -> ExplainerIdentity:
        return ExplainerIdentity(
            name=self.name,
            version=self.version,
            technique=self.technique,
            model_type=self.model_type,
        )

    def explain(
        self,
        path: Path,
        *,
        context: XAIExplanationContext,
        settings: Settings,
    ) -> XAIResult:
        detection = context.detection
        model = XAIModelIdentity(
            name=detection.detector.model_name,
            version=detection.detector.model_version,
            checkpoint_sha256=detection.detector.checkpoint_sha256,
        )
        if detection.prediction is None:
            reason = (
                "no detector model produced a prediction; XAI requires a real "
                "model inference to explain"
            )
            if detection.inference.reason:
                reason = f"{reason} (detection: {detection.inference.reason})"
            return XAIResult(
                status="UNAVAILABLE",
                reason=reason,
                explainer=self.identity,
                model=model,
            )
        model_label = detection.detector.model_name or "unknown"
        return XAIResult(
            status="UNAVAILABLE",
            reason=(
                f"no compatible detector model is registered for XAI in this "
                f"build (model {model_label!r} has no registered explainer)"
            ),
            explainer=self.identity,
            model=model,
        )
