"""Bounded image loading for forensic analyzers.

Images are untrusted input. Loading is capped by an explicit maximum pixel count
(``forensics_max_pixels``) in addition to Pillow's built-in
``MAX_IMAGE_PIXELS`` decompression-bomb guard. Only grayscale (``L``) decoding
is exposed — analyzers do not need color channels.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from app.forensics.base import ForensicError


@dataclass(frozen=True)
class ImageInfo:
    """Header-level facts shared by all analyzer results."""

    format: str | None
    width: int
    height: int
    mode: str


def validate_image_size(path: Path, *, max_pixels: int) -> ImageInfo:
    """Read header, verify integrity, and enforce the pixel cap.

    Raises ``ForensicError`` for unreadable/corrupt/oversized images.
    """
    try:
        with Image.open(path) as image:
            width, height = image.size
            fmt = image.format
        with Image.open(path) as image:
            image.verify()
    except DecompressionBombError as exc:
        raise ForensicError(
            "image exceeds the maximum supported pixel dimensions for forensics"
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ForensicError("stored file is not a readable image") from exc

    if width * height > max_pixels:
        raise ForensicError(
            f"image exceeds the configured forensics pixel limit ({max_pixels})"
        )
    return ImageInfo(format=fmt, width=width, height=height, mode="L")


def load_grayscale(path: Path, *, max_pixels: int) -> np.ndarray:
    """Decode the image as a bounded uint8 grayscale array.

    The pixel cap is enforced by ``validate_image_size`` before decoding, so a
    hostile image can never force a full-resolution allocation.
    """
    validate_image_size(path, max_pixels=max_pixels)
    try:
        with Image.open(path) as image:
            return np.asarray(image.convert("L"), dtype=np.uint8)
    except (DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ForensicError("stored file is not a readable image") from exc
