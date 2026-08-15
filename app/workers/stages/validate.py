"""``validate`` pipeline stage: stored-media integrity check.

Real behavior: the stored file must exist and its bytes must match the SHA-256
recorded at ingestion. This is a pre-flight gate for downstream analysis, not a
forensic result.
"""

import asyncio

from app.domain.taxonomy import MediaType
from app.media.hashing import sha256_of_file
from app.workers.stages.base import StageContext, StageError, StageResult


class ValidateStage:
    """Verifies the stored file exists and matches its recorded fingerprint."""

    name = "validate"

    async def run(self, ctx: StageContext) -> StageResult | None:
        if ctx.media.media_type is not MediaType.IMAGE:
            raise StageError(
                f"media type {ctx.media.media_type.value} is not supported by the pipeline"
            )
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except Exception as exc:
            raise StageError("invalid storage reference") from exc
        if not path.exists():
            raise StageError("stored media file is missing")
        actual = await asyncio.to_thread(sha256_of_file, path)
        if ctx.media.sha256 is not None and actual != ctx.media.sha256:
            raise StageError(
                "sha256 mismatch between database record and stored file"
            )
        return None
