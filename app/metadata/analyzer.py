"""Metadata consistency analysis.

Computes only checks that are defensible from verified metadata. Findings carry
an ``EvidenceType`` and neutral wording: metadata presence/absence is an
observation, never a manipulation verdict, and editing-software metadata is
evidence of processing, never of AI generation.
"""

from dataclasses import dataclass
from datetime import datetime

from app.domain.taxonomy import EvidenceType
from app.metadata.extractor import ExtractedMetadata

# Detected format -> expected recorded MIME (from the ingestion allowlist).
_FORMAT_EXPECTED_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

# Known editor/processing software markers (case-insensitive substring).
_EDITOR_MARKERS: tuple[tuple[str, str], ...] = (
    ("photoshop", "Adobe Photoshop"),
    ("lightroom", "Adobe Lightroom"),
    ("adobe dng", "Adobe DNG"),
    ("adobe", "Adobe"),
    ("gimp", "GIMP"),
    ("paint.net", "Paint.NET"),
    ("affinity", "Affinity Photo"),
    ("canva", "Canva"),
    ("snapseed", "Snapseed"),
    ("photoscape", "PhotoScape"),
    ("pixlr", "Pixlr"),
    ("darktable", "darktable"),
    ("digikam", "digiKam"),
)


@dataclass(frozen=True)
class Finding:
    """One metadata consistency observation."""

    code: str
    evidence_type: EvidenceType
    message: str


def analyze_metadata(
    extracted: ExtractedMetadata, *, recorded_mime: str | None
) -> tuple[Finding, ...]:
    """Derive findings from extracted metadata and the ingestion record."""
    findings: list[Finding] = []

    _check_orientation(extracted, findings)
    _check_capture_vs_modification(extracted, findings)
    _check_iso(extracted, findings)
    _check_exposure(extracted, findings)
    _check_gps(extracted, findings)
    _check_software(extracted, findings)
    _check_format_mismatch(extracted, recorded_mime, findings)

    findings.sort(key=lambda f: f.code)
    return tuple(findings)


def _check_orientation(extracted: ExtractedMetadata, findings: list[Finding]) -> None:
    orientation = extracted.exif.orientation
    if orientation is not None and not 1 <= orientation <= 8:
        findings.append(
            Finding(
                code="exif_orientation_out_of_range",
                evidence_type=EvidenceType.VERIFIED,
                message=(
                    f"EXIF orientation value {orientation} is outside the "
                    "valid EXIF range (1-8)"
                ),
            )
        )


def _check_capture_vs_modification(
    extracted: ExtractedMetadata, findings: list[Finding]
) -> None:
    captured = _parse_iso(extracted.exif.captured_at)
    modified = _parse_iso(extracted.exif.modified_at)
    if captured is None or modified is None:
        return
    if captured > modified:
        findings.append(
            Finding(
                code="capture_later_than_modification",
                evidence_type=EvidenceType.HEURISTIC,
                message=(
                    "EXIF capture timestamp is later than the EXIF modification "
                    "timestamp; this is contradictory but does not establish "
                    "manipulation on its own"
                ),
            )
        )


def _check_iso(extracted: ExtractedMetadata, findings: list[Finding]) -> None:
    iso = extracted.exif.iso_speed_ratings
    if iso is not None and iso <= 0:
        findings.append(
            Finding(
                code="implausible_iso",
                evidence_type=EvidenceType.VERIFIED,
                message=f"EXIF ISO speed rating {iso} is implausible (must be positive)",
            )
        )


def _check_exposure(extracted: ExtractedMetadata, findings: list[Finding]) -> None:
    exposure = extracted.exif.exposure_time
    if exposure is not None and exposure <= 0:
        findings.append(
            Finding(
                code="implausible_exposure_time",
                evidence_type=EvidenceType.VERIFIED,
                message="EXIF exposure time is not positive",
            )
        )


def _check_gps(extracted: ExtractedMetadata, findings: list[Finding]) -> None:
    if extracted.exif.gps.present:
        findings.append(
            Finding(
                code="gps_present",
                evidence_type=EvidenceType.VERIFIED,
                message="GPS coordinates are present in the metadata (privacy-sensitive)",
            )
        )


def _check_software(extracted: ExtractedMetadata, findings: list[Finding]) -> None:
    values = list(extracted.exif.software)
    if extracted.xmp.creator_tool:
        values.append(extracted.xmp.creator_tool)
    values.extend(extracted.xmp.software)
    for value in values:
        matched = _editor_label(value)
        if matched is not None:
            findings.append(
                Finding(
                    code="editing_software_metadata",
                    evidence_type=EvidenceType.VERIFIED,
                    message=(
                        f"software metadata indicates processing by {matched}; "
                        "this does not establish AI generation"
                    ),
                )
            )
            return


def _check_format_mismatch(
    extracted: ExtractedMetadata, recorded_mime: str | None, findings: list[Finding]
) -> None:
    if not recorded_mime or not extracted.format:
        return
    expected = _FORMAT_EXPECTED_MIME.get(extracted.format)
    if expected is not None and recorded_mime != expected:
        findings.append(
            Finding(
                code="format_mime_mismatch",
                evidence_type=EvidenceType.VERIFIED,
                message=(
                    f"detected image format {extracted.format} does not match "
                    f"the recorded mime type {recorded_mime}"
                ),
            )
        )


def _editor_label(value: str) -> str | None:
    lowered = value.lower()
    for marker, label in _EDITOR_MARKERS:
        if marker in lowered:
            return label
    return None


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
