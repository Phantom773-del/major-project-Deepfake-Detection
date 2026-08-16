"""Error Level Analysis (ELA).

ELA measures how much a compressed image changes when it is compressed AGAIN:
a fresh (single-generation) JPEG loses little on a second pass; an already
re-saved region usually shows larger error. This is a MEASUREMENT, not a
verdict. ELA error depends on compression history, JPEG quality, and image
content — a high ELA value is NOT proof of manipulation or AI generation.

Algorithm (deterministic):
1. decode the stored file as bounded grayscale (``L``)
2. encode to JPEG at ``quality`` (in-memory, no temp files) and decode
3. encode that decode again at the same quality and decode
4. difference = abs(first_pass - second_pass) per pixel
5. summarize: mean abs error, max error, p95/p99, error ratio

Why two passes? Encoding an already-JPEG file again is the classic ELA probe;
for a non-JPEG source the first pass establishes the baseline. Both passes use
the same quality so the comparison is apples-to-apples.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import Settings
from app.domain.taxonomy import EvidenceType, MediaType
from app.forensics.image import load_grayscale
from app.forensics.result import AnalyzerResult, ForensicFinding


class ErrorLevelAnalyzer:
    """Single-generation recompression sensitivity measurement."""

    name = "ela"
    media_type = MediaType.IMAGE
    version = "1"

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        quality = settings.ela_jpeg_quality
        array = load_grayscale(path, max_pixels=settings.forensics_max_pixels)
        first = _jpeg_pass(array, quality)
        second = _jpeg_pass(first, quality)
        error = np.abs(first.astype(np.int16) - second.astype(np.int16))
        mean_abs = float(np.mean(error))
        max_error = int(np.max(error))
        p95 = float(np.percentile(error, 95))
        p99 = float(np.percentile(error, 99))
        error_ratio = float(np.mean(error > 0))
        measurements = {
            "mean_abs_error": mean_abs,
            "max_error": max_error,
            "p95_error": p95,
            "p99_error": p99,
            "error_ratio": error_ratio,
        }
        findings = (
            ForensicFinding(
                code="ela_measured",
                evidence_type=EvidenceType.VERIFIED,
                message=(
                    f"Measured ELA at JPEG quality {quality}: mean absolute "
                    f"error {mean_abs}, error ratio {error_ratio:.4f}"
                ),
            ),
            ForensicFinding(
                code="ela_interpretation",
                evidence_type=EvidenceType.HEURISTIC,
                message=(
                    "ELA is a supporting signal only: it is affected by "
                    "compression history and image content and does not by "
                    "itself establish manipulation or AI generation"
                ),
            ),
        )
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="COMPLETED",
            measurements=measurements,
            parameters={"quality": quality},
            findings=findings,
        )


def _jpeg_pass(array: np.ndarray, quality: int) -> np.ndarray:
    """Encode a uint8 grayscale array to JPEG at ``quality`` and decode it."""
    image = Image.fromarray(array, mode="L")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as reloaded:
        return np.asarray(reloaded.convert("L"), dtype=np.uint8)
