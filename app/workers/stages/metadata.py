"""``metadata`` pipeline stage: metadata intelligence for images.

Extracts real, normalized metadata (EXIF/XMP/GPS/ICC, dimensions, format) from
the stored file and writes a structured, evidence-classified result to the
stage's ``result_ref``. Metadata is evidence — the stage never decides
REAL/FAKE/AI-GENERATED/MANIPULATED.
"""

import asyncio
import json

from app.domain.taxonomy import MediaType
from app.metadata.analyzer import analyze_metadata
from app.metadata.extractor import MetadataExtractionError, extract_image_metadata
from app.metadata.result import build_metadata_payload
from app.workers.stages.base import StageContext, StageError, StageResult


class MetadataStage:
    """Extracts and normalizes the metadata actually present in the media."""

    name = "metadata"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the "
                "metadata stage"
            )
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except Exception as exc:  # noqa: BLE001 - any resolver failure is client-safe
            raise StageError("invalid storage reference") from exc
        if not path.exists():
            raise StageError("stored media file is missing")
        try:
            extracted = await asyncio.to_thread(extract_image_metadata, path)
        except MetadataExtractionError as exc:
            raise StageError(exc.message) from exc
        findings = analyze_metadata(extracted, recorded_mime=ctx.media.mime_type)
        payload = build_metadata_payload(extracted, findings)
        return StageResult(result_ref=json.dumps(payload, sort_keys=True))
