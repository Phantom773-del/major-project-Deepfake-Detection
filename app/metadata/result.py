"""Normalized metadata result payload (the ``metadata`` stage result_ref).

Maps the internal extraction/analysis structures into the stable JSON contract
documented in ``docs/API_CONTRACTS.md``. Absent fields are ``null`` — nothing is
invented. Provenance (C2PA) is intentionally reported as unavailable until a
real parser exists.
"""

from app.metadata.analyzer import Finding
from app.metadata.extractor import ExtractedMetadata


def build_metadata_payload(
    extracted: ExtractedMetadata, findings: tuple[Finding, ...]
) -> dict[str, object]:
    """Return the deterministic JSON-serializable metadata payload."""
    software = _merged_software(extracted)
    exif = extracted.exif
    gps = exif.gps
    xmp = extracted.xmp
    return {
        "format": extracted.format,
        "mode": extracted.mode,
        "dimensions": {
            "width": extracted.width,
            "height": extracted.height,
        },
        "exif": {
            "present": exif.present,
            "camera_make": exif.camera_make,
            "camera_model": exif.camera_model,
            "captured_at": exif.captured_at,
            "modified_at": exif.modified_at,
            "software": list(exif.software),
            "orientation": exif.orientation,
            "exposure_time": exif.exposure_time,
            "f_number": exif.f_number,
            "iso_speed_ratings": exif.iso_speed_ratings,
            "focal_length": exif.focal_length,
            "flash": exif.flash,
            "white_balance": exif.white_balance,
            "image_description": exif.image_description,
            "artist": exif.artist,
            "copyright": exif.copyright,
            "lens_make": exif.lens_make,
            "lens_model": exif.lens_model,
        },
        "gps": {
            "present": gps.present,
            "latitude": gps.latitude,
            "longitude": gps.longitude,
            "altitude_m": gps.altitude_m,
            "date_stamp": gps.date_stamp,
        },
        "xmp": {
            "present": xmp.present,
            "creator_tool": xmp.creator_tool,
            "create_date": xmp.create_date,
            "modify_date": xmp.modify_date,
            "metadata_date": xmp.metadata_date,
            "creators": list(xmp.creators),
            "rights": xmp.rights,
            "title": xmp.title,
            "description": xmp.description,
            "format": xmp.format,
            "software": list(xmp.software),
        },
        "icc": {
            "present": extracted.icc_profile_present,
        },
        "presence": {
            "exif": exif.present,
            "xmp": xmp.present,
            "icc": extracted.icc_profile_present,
            "gps": gps.present,
        },
        "software": list(software),
        "consistency": {
            "findings": [_finding_dict(f) for f in findings],
            "count": len(findings),
        },
        "provenance": {
            "status": "UNAVAILABLE",
            "note": "C2PA/manifest provenance parsing is not implemented in this build",
        },
        "extractor": {
            "library": "Pillow",
            "errors": list(extracted.extractor_errors),
        },
    }


def _finding_dict(finding: Finding) -> dict[str, str]:
    return {
        "code": finding.code,
        "evidence_type": finding.evidence_type.value,
        "message": finding.message,
    }


def _merged_software(extracted: ExtractedMetadata) -> tuple[str, ...]:
    """Merge EXIF + XMP software into one deduplicated, bounded list."""
    seen: set[str] = set()
    merged: list[str] = []
    for value in list(extracted.exif.software) + list(extracted.xmp.software):
        if value and value not in seen:
            seen.add(value)
            merged.append(value)
    return tuple(merged[:10])
