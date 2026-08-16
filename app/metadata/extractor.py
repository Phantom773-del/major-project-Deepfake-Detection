"""Safe, read-only metadata extraction from image files.

Wraps Pillow so the analysis pipeline gets normalized, deterministic metadata.
Every value comes from actual file parsing — nothing is invented. Extraction is
strictly read-only: no modification, no thumbnail writes, no side effects.

Security model:
- ``defusedxml`` powers Pillow's ``getxmp()`` (safe XML parsing, no entity
  expansion), so malformed or hostile XMP packets cannot crash the worker.
- PIL ``Image.open`` is bounded by Pillow's ``MAX_IMAGE_PIXELS``
  (DecompressionBombError) — caught and surfaced as a client-safe error.
- Parser exceptions (corrupt EXIF IFD, malformed timestamps, bad XMP) are
  caught per-section and recorded as ``extractor_errors`` instead of aborting
  the whole stage; only an unparseable file fails the stage.
"""

from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

# Length / count bounds so hostile metadata stays bounded in memory.
_MAX_TEXT_LENGTH = 1000
_MAX_LIST_ENTRIES = 10

# Canonical EXIF tag ids (stable across Pillow versions).
_TAG_MAKE = 0x010F
_TAG_MODEL = 0x0110
_TAG_ORIENTATION = 0x0112
_TAG_SOFTWARE = 0x0131
_TAG_DATETIME = 0x0132
_TAG_IMAGE_DESCRIPTION = 0x010E
_TAG_ARTIST = 0x013B
_TAG_EXPOSURE_TIME = 0x829A
_TAG_FNUMBER = 0x829D
_TAG_ISO = 0x8827
_TAG_FLASH = 0x9209
_TAG_FOCAL_LENGTH = 0x920A
_TAG_COPYRIGHT = 0x8298
_TAG_DATETIME_ORIGINAL = 0x9003
_TAG_WHITE_BALANCE = 0xA403
_TAG_LENS_MAKE = 0xA433
_TAG_LENS_MODEL = 0xA434

# GPSInfo IFD sub-tag ids.
_GPS_LAT_REF = 0x0001
_GPS_LAT = 0x0002
_GPS_LON_REF = 0x0003
_GPS_LON = 0x0004
_GPS_ALT = 0x0006
_GPS_DATE_STAMP = 0x001D


class MetadataExtractionError(Exception):
    """The stored file cannot be parsed as a supported image.

    ``message`` is client-safe (no paths, no tracebacks).
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class GpsMetadata:
    """Normalized GPS block (present only when a GPS IFD exists)."""

    present: bool
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    date_stamp: str | None = None


@dataclass(frozen=True)
class ExifMetadata:
    """Normalized subset of the EXIF/TIFF tags that are actually exposed."""

    present: bool
    camera_make: str | None = None
    camera_model: str | None = None
    captured_at: str | None = None
    modified_at: str | None = None
    software: tuple[str, ...] = ()
    orientation: int | None = None
    exposure_time: float | None = None
    f_number: float | None = None
    iso_speed_ratings: int | None = None
    focal_length: float | None = None
    flash: int | None = None
    white_balance: int | None = None
    image_description: str | None = None
    artist: str | None = None
    copyright: str | None = None
    lens_make: str | None = None
    lens_model: str | None = None
    gps: GpsMetadata = GpsMetadata(present=False)


@dataclass(frozen=True)
class XmpMetadata:
    """Normalized subset of the XMP packet (read via Pillow + defusedxml)."""

    present: bool
    creator_tool: str | None = None
    create_date: str | None = None
    modify_date: str | None = None
    metadata_date: str | None = None
    creators: tuple[str, ...] = ()
    rights: str | None = None
    title: str | None = None
    description: str | None = None
    format: str | None = None
    software: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedMetadata:
    """Everything the metadata stage needs, in stable application terms."""

    format: str | None
    mode: str | None
    width: int
    height: int
    exif: ExifMetadata
    xmp: XmpMetadata
    icc_profile_present: bool
    extractor_errors: tuple[str, ...]


def extract_image_metadata(path: Path) -> ExtractedMetadata:
    """Extract and normalize metadata from an image file.

    Raises MetadataExtractionError for unreadable/corrupt/decompression-bomb
    files. Section-level parse failures degrade gracefully into
    ``extractor_errors`` instead of failing the extraction.
    """
    try:
        with Image.open(path) as image:
            return _extract_from_open(image)
    except DecompressionBombError as exc:
        raise MetadataExtractionError(
            "image exceeds the maximum supported pixel dimensions"
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MetadataExtractionError(
            "stored file is not a readable image"
        ) from exc


def _extract_from_open(image: Image.Image) -> ExtractedMetadata:
    errors: list[str] = []
    try:
        fmt = image.format
        mode = image.mode
        width, height = image.size
    except (OSError, ValueError, TypeError) as exc:
        raise MetadataExtractionError("stored file is not a readable image") from exc

    icc = bool(image.info.get("icc_profile"))

    exif = _extract_exif(image, errors)
    xmp = _extract_xmp(image, errors)
    return ExtractedMetadata(
        format=fmt,
        mode=mode,
        width=int(width),
        height=int(height),
        exif=exif,
        xmp=xmp,
        icc_profile_present=icc,
        extractor_errors=tuple(_truncate(e) for e in errors),
    )


def _extract_exif(image: Image.Image, errors: list[str]) -> ExifMetadata:
    try:
        raw = image.getexif()
    except Exception as exc:  # noqa: BLE001 - corrupt IFD may raise anything
        errors.append(f"exif: {_truncate(str(exc))}")
        return ExifMetadata(present=False)

    present = len(raw) > 0 or bool(_gps_ifd(raw))
    gps = _extract_gps(raw)
    software = tuple(
        _truncate(v)
        for v in _as_list(raw.get(_TAG_SOFTWARE))
        if _truncate(v)
    )
    return ExifMetadata(
        present=present,
        camera_make=_text(raw.get(_TAG_MAKE)),
        camera_model=_text(raw.get(_TAG_MODEL)),
        captured_at=_normalize_exif_datetime(raw.get(_TAG_DATETIME_ORIGINAL), errors),
        modified_at=_normalize_exif_datetime(raw.get(_TAG_DATETIME), errors),
        software=software[:_MAX_LIST_ENTRIES],
        orientation=_int_or_none(raw.get(_TAG_ORIENTATION)),
        exposure_time=_rational(raw.get(_TAG_EXPOSURE_TIME)),
        f_number=_rational(raw.get(_TAG_FNUMBER)),
        iso_speed_ratings=_int_or_none(raw.get(_TAG_ISO)),
        focal_length=_rational(raw.get(_TAG_FOCAL_LENGTH)),
        flash=_int_or_none(raw.get(_TAG_FLASH)),
        white_balance=_int_or_none(raw.get(_TAG_WHITE_BALANCE)),
        image_description=_text(raw.get(_TAG_IMAGE_DESCRIPTION)),
        artist=_text(raw.get(_TAG_ARTIST)),
        copyright=_text(raw.get(_TAG_COPYRIGHT)),
        lens_make=_text(raw.get(_TAG_LENS_MAKE)),
        lens_model=_text(raw.get(_TAG_LENS_MODEL)),
        gps=gps,
    )


def _gps_ifd(raw: Image.Exif) -> dict[int, object]:
    try:
        return raw.get_ifd(ExifTags.IFD.GPSInfo)
    except Exception:  # noqa: BLE001 - malformed GPS IFD must not crash
        return {}


def _extract_gps(raw: Image.Exif) -> GpsMetadata:
    ifd = _gps_ifd(raw)
    if not ifd:
        return GpsMetadata(present=False)
    lat = _gps_degrees(ifd.get(_GPS_LAT), ifd.get(_GPS_LAT_REF), "S")
    lon = _gps_degrees(ifd.get(_GPS_LON), ifd.get(_GPS_LON_REF), "W")
    alt = _rational(ifd.get(_GPS_ALT))
    stamp = _text(ifd.get(_GPS_DATE_STAMP))
    return GpsMetadata(
        present=True,
        latitude=lat,
        longitude=lon,
        altitude_m=alt,
        date_stamp=_truncate(stamp) if stamp else None,
    )


def _gps_degrees(
    value: object, ref: object, negative_ref: str
) -> float | None:
    """Convert an EXIF deg/min/sec rational tuple to signed decimal degrees."""
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    parts = [_rational(v, allow_zero=True) for v in value]
    if any(p is None for p in parts):
        return None
    deg, minutes, seconds = parts
    if deg is None or minutes is None or seconds is None:
        return None
    signed = deg + minutes / 60.0 + seconds / 3600.0
    if isinstance(ref, str) and ref.strip().upper() == negative_ref:
        signed = -signed
    return round(signed, 7)


def _extract_xmp(image: Image.Image, errors: list[str]) -> XmpMetadata:
    try:
        raw = image.getxmp()
    except Exception as exc:  # noqa: BLE001 - hostile XMP must not crash
        errors.append(f"xmp: {_truncate(str(exc))}")
        return XmpMetadata(present=False)
    if not raw:
        return XmpMetadata(present=False)
    desc = _xmp_description(raw)
    return XmpMetadata(
        present=True,
        creator_tool=_xmp_text(desc.get("CreatorTool")),
        create_date=_xmp_text(desc.get("CreateDate")),
        modify_date=_xmp_text(desc.get("ModifyDate")),
        metadata_date=_xmp_text(desc.get("MetadataDate")),
        creators=tuple(
            _truncate(v) for v in _xmp_list(desc.get("creator"))[: _MAX_LIST_ENTRIES]
        ),
        rights=_xmp_text(desc.get("rights")),
        title=_xmp_text(desc.get("title")),
        description=_xmp_text(desc.get("description")),
        format=_xmp_text(desc.get("format")),
        software=tuple(
            _truncate(v) for v in _xmp_list(desc.get("Software"))[: _MAX_LIST_ENTRIES]
        ),
    )


def _xmp_description(raw: dict[str, object]) -> dict[str, object]:
    """Drill into Pillow's ``getxmp()`` result to the Description object."""
    xmpmeta = raw.get("xmpmeta")
    if not isinstance(xmpmeta, dict):
        return {}
    rdf = xmpmeta.get("RDF")
    if not isinstance(rdf, dict):
        return {}
    desc = rdf.get("Description")
    if not isinstance(desc, dict):
        return {}
    return desc


def _xmp_plain(value: object) -> str | None:
    """Extract a plain string from a nested XMP value (string or RDF node)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str):
            return text
    return None


def _xmp_text(value: object) -> str | None:
    plain = _xmp_plain(value)
    if plain is None:
        return None
    return _truncate(plain)


def _xmp_list(value: object) -> list[str]:
    """Collect strings from an XMP value, unwrapping Alt/Seq/Bag containers."""
    plain = _xmp_plain(value)
    if plain is not None:
        return [plain]
    if isinstance(value, dict):
        for key in ("Alt", "Seq", "Bag"):
            if key in value:
                return _xmp_list(value[key])
        li = value.get("li")
        if li is not None:
            items = li if isinstance(li, list) else [li]
            return [v for v in (_xmp_plain(item) for item in items) if v is not None]
    return []


def _normalize_exif_datetime(value: object, errors: list[str]) -> str | None:
    """Normalize ``YYYY:MM:DD HH:MM:SS`` EXIF timestamps to ISO 8601.

    EXIF timestamps carry no timezone; the output therefore has no offset
    (timezone is unknown, never assumed to be UTC).
    """
    text = _text(value)
    if text is None:
        return None
    try:
        from datetime import datetime

        parsed = datetime.strptime(text, "%Y:%m:%d %H:%M:%S")
    except ValueError:
        errors.append("exif: unparseable datetime")
        return None
    return parsed.isoformat()


def _text(value: object) -> str | None:
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            return None
    if isinstance(value, str):
        value = value.strip()
        return _truncate(value) if value else None
    return None


def _as_list(value: object) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_text(v) or "" for v in value]
    text = _text(value)
    return [text] if text else []


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _rational(value: object, *, allow_zero: bool = False) -> float | None:
    """Convert a rational (``IFDRational``/fraction) to a rounded float."""
    try:
        if isinstance(value, bool) or value is None:
            return None
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    if number != number:  # NaN is implausible
        return None
    if not allow_zero and number <= 0:
        return None
    return round(number, 6)


def _truncate(value: str, *, limit: int = _MAX_TEXT_LENGTH) -> str:
    return value if len(value) <= limit else value[:limit] + "…"
