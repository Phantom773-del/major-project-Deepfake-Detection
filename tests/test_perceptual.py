"""Perceptual hash (dHash) tests: determinism and sensitivity."""

from io import BytesIO
from pathlib import Path

from app.media.perceptual import dhash
from PIL import Image


def _gradient_bytes(reversed: bool = False, size: int = 32) -> bytes:
    buf = BytesIO()
    values = [
        (size - 1 - x) * 8 if reversed else x * 8
        for y in range(size)
        for x in range(size)
    ]
    img = Image.new("L", (size, size))
    img.putdata(values)
    img.save(buf, format="PNG")
    return buf.getvalue()


def _image_bytes(color: tuple[int, int, int], width: int = 16, height: int = 16) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _write_image(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_dhash_is_deterministic(tmp_path: Path) -> None:
    a = _write_image(tmp_path / "a.png", _image_bytes((10, 20, 30)))
    b = _write_image(tmp_path / "b.png", _image_bytes((10, 20, 30)))
    assert dhash(a) == dhash(b)


def test_dhash_format_is_64bit_hex(tmp_path: Path) -> None:
    path = _write_image(tmp_path / "a.png", _image_bytes((10, 20, 30)))
    value = dhash(path)
    assert len(value) == 16
    int(value, 16)


def test_dhash_differs_for_different_images(tmp_path: Path) -> None:
    a = _write_image(tmp_path / "a.png", _gradient_bytes(reversed=False))
    b = _write_image(tmp_path / "b.png", _gradient_bytes(reversed=True))
    assert dhash(a) != dhash(b)


def test_dhash_stable_across_reloads(tmp_path: Path) -> None:
    path = tmp_path / "a.png"
    content = _image_bytes((60, 70, 80))
    path.write_bytes(content)
    first = dhash(path)
    path.write_bytes(content)
    assert dhash(path) == first
