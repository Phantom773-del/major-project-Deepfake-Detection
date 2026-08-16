"""``xai`` pipeline stage: explainability for the detector's actual inference.

Resolves the stored media, reads the detection result the pipeline actually
produced (from the ``detect`` stage's ``result_ref``), re-resolves the SAME
detector instance by name, and asks a registered explainer to explain that
inference. The stage never loads its own checkpoint and never invents a heatmap:
without a compatible detector model it returns an explicit UNAVAILABLE payload,
and the stage itself COMPLETES — UNAVAILABLE is an honest state, not an error.
"""

import asyncio
import json
import logging
from typing import Any

from app.domain.taxonomy import MediaType
from app.inference.base import DetectionResult
from app.inference.detectors import build_default_detector_registry
from app.inference.registry import DetectorRegistry
from app.workers.stages.base import StageContext, StageError, StageResult
from app.xai.base import (
    XAIError,
    XAIExplanationContext,
    XAIResult,
)
from app.xai.explainers import build_default_xai_explainer_registry
from app.xai.registry import XAIExplainerRegistry

logger = logging.getLogger(__name__)


class XAIStage:
    """Explains the detection result for the media type, if any model exists."""

    name = "xai"

    def __init__(
        self,
        explainers: XAIExplainerRegistry | None = None,
        detectors: DetectorRegistry | None = None,
    ) -> None:
        self.explainers = (
            explainers if explainers is not None else build_default_xai_explainer_registry()
        )
        self.detectors = (
            detectors if detectors is not None else build_default_detector_registry()
        )

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "xai stage"
            )
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except Exception as exc:  # noqa: BLE001 - any resolver failure is client-safe
            raise StageError("invalid storage reference") from exc
        if not path.exists():
            raise StageError("stored media file is missing")

        detection = self._detection_result(ctx)
        if detection is None:
            return StageResult(
                result_ref=self._unavailable("no detection result is available for XAI")
            )

        detector = self.detectors.get(detection.detector.name)
        if detector is None:
            return StageResult(
                result_ref=self._unavailable(
                    f"detector {detection.detector.name!r} used for detection is "
                    "not registered"
                )
            )

        explainer = self.explainers.find(
            detection.media_type, detection.detector.model_name
        )
        if explainer is None:
            model_label = detection.detector.model_name or "unknown"
            return StageResult(
                result_ref=self._unavailable(
                    f"no XAI explainer is registered for model {model_label!r}"
                )
            )

        context = XAIExplanationContext(
            detector=detector,
            detection=detection,
            device=ctx.settings.detection_device,
        )
        try:
            result = await asyncio.to_thread(
                explainer.explain, path, context=context, settings=ctx.settings
            )
        except XAIError as exc:
            raise StageError(exc.message) from exc
        except Exception:
            logger.exception("xai explainer %s failed unexpectedly", explainer.name)
            raise StageError("unexpected xai failure") from None

        return StageResult(
            result_ref=json.dumps(result.model_dump(mode="json"), sort_keys=True)
        )

    @staticmethod
    def _unavailable(reason: str) -> str:
        result = XAIResult(status="UNAVAILABLE", reason=reason)
        return json.dumps(result.model_dump(mode="json"), sort_keys=True)

    @staticmethod
    def _detection_result(ctx: StageContext) -> DetectionResult | None:
        """Read the detect stage's persisted result from the scan's stages."""
        stage = next((s for s in ctx.scan.stages if s.name == "detect"), None)
        if stage is None or stage.result_ref is None:
            return None
        try:
            payload: dict[str, Any] = json.loads(stage.result_ref)
            return DetectionResult.model_validate(payload)
        except Exception:
            logger.warning("could not parse detect result for scan %s", ctx.scan.id)
            return None
