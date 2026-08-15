"""Perceptual image hashing (dHash).

A real, deterministic 64-bit perceptual hash computed from decoded pixel
luminance. A dHash match means structural visual similarity — it is NOT proof
of identical provenance and must never be presented as forensic truth.
"""

from pathlib import Path

from PIL import Image


def dhash(path: Path, *, hash_size: int = 8) -> str:
    """Return a ``hash_size * hash_size`` bit dHash as lowercase hex."""
    with Image.open(path) as image:
        gray = image.convert("L").resize(
            (hash_size + 1, hash_size), Image.Resampling.LANCZOS
        )
    width, _height = gray.size
    pixels = list(gray.tobytes())
    bits = [
        int(pixels[row * width + col] > pixels[row * width + col + 1])
        for row in range(hash_size)
        for col in range(hash_size)
    ]
    value = int("".join(str(bit) for bit in bits), 2)
    return f"{value:0{hash_size * hash_size // 4}x}"
