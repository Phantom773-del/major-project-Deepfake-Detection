"""Noise / residual analysis.

Removes a low-frequency estimate (Gaussian blur) from the grayscale image and
summarizes the residual statistics. This is a MEASUREMENT of local high-frequency
content, not an authenticity signal: residual characteristics depend on the
camera/sensor, ISO, compression, resizing, denoising, image content, and editing
history. High or low residual energy is NOT proof of AI generation.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from app.core.config import Settings
from app.domain.taxonomy import EvidenceType, MediaType
from app.forensics.image import load_grayscale
from app.forensics.result import AnalyzerResult, ForensicFinding


class NoiseResidualAnalyzer:
    """Local high-frequency residual statistics after Gaussian smoothing."""

    name = "noise"
    media_type = MediaType.IMAGE
    version = "1"

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        radius = settings.noise_blur_radius
        array = load_grayscale(path, max_pixels=settings.forensics_max_pixels)
        image = Image.fromarray(array, mode="L")
        smoothed = np.asarray(
            image.filter(ImageFilter.GaussianBlur(radius=radius)).convert("L"),
            dtype=np.float64,
        )
        residual = array.astype(np.float64) - smoothed
        mean = float(np.mean(residual))
        std = float(np.std(residual))
        energy = float(np.mean(residual**2))
        p99_abs = float(np.percentile(np.abs(residual), 99))
        nonzero_ratio = float(np.mean(np.abs(residual) > 0.0))
        measurements = {
            "residual_mean": mean,
            "residual_std": std,
            "residual_energy": energy,
            "p99_abs_residual": p99_abs,
            "nonzero_ratio": nonzero_ratio,
        }
        findings = (
            ForensicFinding(
                code="noise_measured",
                evidence_type=EvidenceType.VERIFIED,
                message=(
                    f"Measured noise residual (Gaussian blur radius {radius}): "
                    f"std {std}, energy {energy}, nonzero ratio {nonzero_ratio:.4f}"
                ),
            ),
            ForensicFinding(
                code="noise_interpretation",
                evidence_type=EvidenceType.HEURISTIC,
                message=(
                    "Noise residual is a supporting signal only: it depends on "
                    "the sensor, ISO, compression, denoising, and content and "
                    "does not establish authenticity by itself"
                ),
            ),
        )
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="COMPLETED",
            measurements=measurements,
            parameters={"blur_radius": radius},
            findings=findings,
        )
