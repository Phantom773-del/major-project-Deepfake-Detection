"""Frequency-domain analysis.

A 2D FFT over the (mean-subtracted) grayscale image, followed by radial energy
band ratios and spectral entropy. This is a MEASUREMENT of where the image's
energy concentrates; no particular frequency signature proves AI generation —
natural photos, compression, resizing, and content all shape the spectrum.

Algorithm (deterministic):
1. bounded grayscale decode, subtract the mean (removes the DC bias)
2. 2D FFT, shifted so DC sits at the center
3. magnitude spectrum; power = magnitude**2
4. radial bands around DC: low (< ``_LOW_FRACTION`` of the minimum dimension),
   mid (between the two fractions), high (beyond the mid radius)
5. band energy ratios (each band power / total power) + normalized spectral
   entropy of the power histogram
"""

import math
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.domain.taxonomy import EvidenceType, MediaType
from app.forensics.image import load_grayscale
from app.forensics.result import AnalyzerResult, ForensicFinding

_LOW_FRACTION = 0.1  # low band radius, as a fraction of the minimum dimension
_MID_FRACTION = 0.3  # mid band outer radius, as a fraction of the minimum dimension
_ENTROPY_BINS = 256  # histogram bins for spectral entropy


class FrequencyAnalyzer:
    """Radial spectral energy distribution and spectral entropy."""

    name = "frequency"
    media_type = MediaType.IMAGE
    version = "1"

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        array = load_grayscale(path, max_pixels=settings.forensics_max_pixels)
        spectrum = _magnitude_spectrum(array)
        power = spectrum**2
        total = float(power.sum())
        if total <= 0.0:
            total = 1.0
        rows, cols = spectrum.shape
        center_y = rows / 2
        center_x = cols / 2
        yy, xx = np.mgrid[0:rows, 0:cols]
        radius = np.sqrt((yy - center_y) ** 2 + (xx - center_x) ** 2)
        min_dim = min(rows, cols)
        low_radius = _LOW_FRACTION * min_dim
        mid_radius = _MID_FRACTION * min_dim
        low = power[radius <= low_radius].sum()
        mid = power[(radius > low_radius) & (radius <= mid_radius)].sum()
        high = power[radius > mid_radius].sum()
        low_ratio = float(low / total)
        mid_ratio = float(mid / total)
        high_ratio = float(high / total)
        entropy = _spectral_entropy(power)
        measurements = {
            "low_energy_ratio": low_ratio,
            "mid_energy_ratio": mid_ratio,
            "high_energy_ratio": high_ratio,
            "spectral_entropy": entropy,
        }
        parameters = {
            "low_fraction": _LOW_FRACTION,
            "mid_fraction": _MID_FRACTION,
            "entropy_bins": _ENTROPY_BINS,
        }
        findings = (
            ForensicFinding(
                code="frequency_measured",
                evidence_type=EvidenceType.VERIFIED,
                message=(
                    f"Measured spectral energy bands: low {low_ratio:.4f}, "
                    f"mid {mid_ratio:.4f}, high {high_ratio:.4f}; "
                    f"spectral entropy {entropy:.4f}"
                ),
            ),
            ForensicFinding(
                code="frequency_interpretation",
                evidence_type=EvidenceType.HEURISTIC,
                message=(
                    "Frequency characteristics are a supporting signal only: "
                    "compression, resizing, content, and processing shape the "
                    "spectrum and no frequency signature proves AI generation"
                ),
            ),
        )
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="COMPLETED",
            measurements=measurements,
            parameters=parameters,
            findings=findings,
        )


def _magnitude_spectrum(array: np.ndarray) -> np.ndarray:
    """Return the shifted magnitude spectrum of the mean-subtracted image."""
    centered = array.astype(np.float64) - float(array.mean())
    return np.abs(np.fft.fftshift(np.fft.fft2(centered)))


def _spectral_entropy(power: np.ndarray) -> float:
    """Normalized Shannon entropy of the power histogram (0..1)."""
    histogram, _ = np.histogram(power, bins=_ENTROPY_BINS)
    probabilities = histogram.astype(np.float64)
    total = probabilities.sum()
    if total <= 0.0:
        return 0.0
    probabilities /= total
    nonzero = probabilities[probabilities > 0.0]
    entropy = float(-((nonzero * np.log2(nonzero)).sum()))
    return max(0.0, entropy) / math.log2(_ENTROPY_BINS)
