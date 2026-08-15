"""``fingerprint`` pipeline stage: re-fingerprint the stored file.

Computes the byte-level SHA-256 and a perceptual dHash over the stored file and
writes them to the stage's ``result_ref`` (JSON). The dHash is a real, but
heuristic, signal — never forensic proof.
"""

import asyncio
import json

from app.domain.exceptions import MediaUploadError
from app.media.hashing import sha256_of_file
from app.media.perceptual import dhash
from app.workers.stages.base import StageContext, StageError, StageResult


class FingerprintStage:
    """Re-hashes the stored file and computes a perceptual fingerprint."""

    name = "fingerprint"

    async def run(self, ctx: StageContext) -> StageResult | None:
        try:
            path = ctx.storage.resolve(ctx.media.storage_path)
        except MediaUploadError as exc:
            raise StageError("invalid storage reference") from exc
        try:
            sha256 = await asyncio.to_thread(sha256_of_file, path)
            perceptual = await asyncio.to_thread(dhash, path)
            size_bytes = path.stat().st_size
        except FileNotFoundError as exc:
            raise StageError("stored media file is missing") from exc
        except OSError as exc:
            raise StageError("stored file is not a readable image") from exc
        result = {
            "sha256": sha256,
            "d_hash": perceptual,
            "size_bytes": size_bytes,
        }
        return StageResult(result_ref=json.dumps(result, sort_keys=True))
