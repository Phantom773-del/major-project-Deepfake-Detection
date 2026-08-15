"""Content detection for uploaded media.

Server-side magic-byte and safe-parse validation. The client filename and
Content-Type are never trusted; the detected type is authoritative.

This is media ingestion validation, not a malware scanner.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.domain.exceptions import MediaUploadError
from app.domain.taxonomy import MediaType

# Magic-byte signatures (content-based, independent of filename).
MAGIC_JPEG = bytes.fromhex("FFD8FF")
MAGIC_PNG = bytes.fromhex("89504E470D0A1A0A")
MAGIC_WEBP = b"WEBP"  # appears at offset 8 (after "RIFF" + size)
MAGIC_GIF = b"GIF8"  # known-but-unsupported

# Detected PIL format -> canonical server-side MIME / extension mapping.
FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
FORMAT_TO_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "JPEG": (".jpg", ".jpeg"),
    "PNG": (".png",),
    "WEBP": (".webp",),
}

_MAX_MAGIC_READ = 12


@dataclass(frozen=True)
class DetectedMedia:
    """Result of server-side content detection."""

    media_type: MediaType
    mime_type: str
    format: str
    width: int
    height: int
    canonical_extension: str


def _magic_matches(path: Path) -> str | None:
    """Return a known-but-possibly-unsupported magic name, else None."""
    with path.open("rb") as fh:
        head = fh.read(_MAX_MAGIC_READ)
    if head.startswith(MAGIC_JPEG):
        return "JPEG"
    if head.startswith(MAGIC_PNG):
        return "PNG"
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == MAGIC_WEBP:
        return "WEBP"
    if head.startswith(MAGIC_GIF):
        return "GIF"
    return None


def detect_image(path: Path) -> DetectedMedia:
    """Validate an image file and extract server-side metadata.

    Raises MediaUploadError:
      - EMPTY_FILE      for zero-byte content
      - INVALID_CONTENT when magic bytes are unrecognized or contradict parsing
      - UNSUPPORTED_TYPE for valid-but-not-allowed formats (e.g. GIF)
    """
    if path.stat().st_size == 0:
        raise MediaUploadError("uploaded file is empty", code="EMPTY_FILE")

    magic = _magic_matches(path)
    if magic is None:
        raise MediaUploadError(
            "unrecognized content (not a supported media file)", code="INVALID_CONTENT"
        )
    if magic not in FORMAT_TO_MIME:
        raise MediaUploadError(
            f"format {magic} is recognized but not supported for ingestion",
            code="UNSUPPORTED_TYPE",
        )

    try:
        with Image.open(path) as im:
            width, height = im.size
        with Image.open(path) as im:
            im.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MediaUploadError(
            "file could not be parsed as a valid image", code="INVALID_CONTENT"
        ) from exc

    fmt = magic
    mime = FORMAT_TO_MIME[fmt]
    return DetectedMedia(
        media_type=MediaType.IMAGE,
        mime_type=mime,
        format=fmt,
        width=width,
        height=height,
        canonical_extension=FORMAT_TO_EXTENSIONS[fmt][0],
    )
