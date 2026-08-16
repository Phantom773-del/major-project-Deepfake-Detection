"""``detect`` pipeline stage: AI/deepfake detection via a detector registry.

Resolves the stored media, finds a detector for the media type, runs inference
off the event loop, and writes the structured ``DetectionResult`` to
``result_ref``. With no real model in this build the default detector reports an
explicit UNAVAILABLE result — never a fabricated prediction.
"""

import asyncio
import json
import logging
import time

from app.domain.taxonomy import MediaType
from app.inference.base import DetectionResult, DetectorError
from app.inference.detectors import build_default_detector_registry
from app.inference.registry import DetectorRegistry
from app.workers.stages.base import StageContext, StageError, StageResult

logger = logging.getLogger(__name__)


class DetectionStage:
    """Runs the registered detector for the media type and persists its result."""

    name = "detect"

    def __init__(self, detectors: DetectorRegistry | None = None) -> None:
        self.detectors = detectors or build_default_detector_registry()

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "detection stage"
            )
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except Exception as exc:  # noqa: BLE001 - any resolver failure is client-safe
            raise StageError("invalid storage reference") from exc
        if not path.exists():
            raise StageError("stored media file is missing")

        detector = self.detectors.find(ctx.media.media_type)
        if detector is None:
            raise StageError(
                f"no detector available for media type {ctx.media.media_type.value}"
            )

        device = ctx.settings.detection_device
        try:
            started = time.perf_counter()
            result = await asyncio.to_thread(detector.detect, path, device=device)
            duration_ms = int((time.perf_counter() - started) * 1000)
        except DetectorError as exc:
            raise StageError(exc.message) from exc
        except Exception:
            logger.exception("detection failed for scan %s", ctx.scan.id)
            raise StageError("unexpected detection failure") from None

        result = _with_duration(result, duration_ms, device)
        payload = json.dumps(result.model_dump(mode="json"), sort_keys=True)
        return StageResult(result_ref=payload)


def _with_duration(
    result: DetectionResult, duration_ms: int, device: str
) -> DetectionResult:
    return result.model_copy(
        update={
            "inference": result.inference.model_copy(
                update={"duration_ms": duration_ms, "device": device}
            )
        }
    )
