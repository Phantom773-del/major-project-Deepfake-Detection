"""Metadata Intelligence stage tests (extraction, analysis, payload, pipeline).

Fixture images are crafted entirely from bytes so every injected metadata value
is exact and known (see ``tests/_exif_builder.py``).
"""

import asyncio
import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import MediaType, ScanStatus, StageStatus
from app.media.hashing import sha256_of_bytes
from app.media.storage import LocalStorageProvider
from app.metadata.extractor import MetadataExtractionError, extract_image_metadata
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.execution import ScanExecutionService
from app.services.scans import ScanService
from app.workers.queue import AnalysisWorker
from app.workers.stages import build_default_registry
from app.workers.stages.base import StageContext, StageError
from app.workers.stages.metadata import MetadataStage
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from tests._exif_builder import build_exif_bytes

_XMP_NAMESPACE = b"http://ns.adobe.com/xap/1.0/\x00"

_XMP_SKELETON = (
    b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
    b' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
    b"  <rdf:Description rdf:about=\"\" xmlns:tiff=\"http://ns.adobe.com/tiff/1.0/\""
    b' xmlns:xmp="http://ns.adobe.com/xap/1.0/">\n'
    b"  {body}\n"
    b"  </rdf:Description>\n"
    b" </rdf:RDF>\n"
    b"</x:xmpmeta>\n"
    b'<?xpacket end="w"?>'
)


def _jpeg_bytes(
    exif: bytes | None = None,
    xmp: bytes | None = None,
    *,
    size: tuple[int, int] = (24, 16),
) -> bytes:
    buf = BytesIO()
    image = Image.new("RGB", size, (10, 20, 30))
    if exif is None:
        image.save(buf, format="JPEG")
    else:
        image.save(buf, format="JPEG", exif=exif)
    data = buf.getvalue()
    if xmp is None:
        return data
    app1 = b"\xff\xe1" + (2 + len(_XMP_NAMESPACE) + len(xmp)).to_bytes(2, "big")
    app1 += _XMP_NAMESPACE + xmp
    head, marker, tail = data.partition(b"\xff\xda")
    return head + app1 + marker + tail


def _xmp(body: str) -> bytes:
    return _XMP_SKELETON.replace(b"{body}", body.encode("utf-8"))


def _png_bytes(width: int = 12, height: int = 9) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (120, 40, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _media(*, storage_path: str, mime_type: str | None = "image/jpeg") -> Media:
    return Media(
        original_filename=storage_path,
        media_type=MediaType.IMAGE,
        storage_path=storage_path,
        mime_type=mime_type,
    )


def _scan() -> Scan:
    return Scan(media_id=uuid.uuid4())


def _ctx(tmp_path: Path, media: Media) -> StageContext:
    return StageContext(
        scan=_scan(),
        media=media,
        storage=LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path),
    )


async def _run_stage(
    tmp_path: Path, content: bytes, *, mime_type: str | None = "image/jpeg"
) -> dict[str, Any]:
    name = f"f-{uuid.uuid4().hex}.bin"
    (tmp_path / name).write_bytes(content)
    media = _media(storage_path=name, mime_type=mime_type)
    result = await MetadataStage().run(_ctx(tmp_path, media))
    assert result is not None and result.result_ref is not None
    return cast(dict[str, Any], json.loads(result.result_ref))


async def _queued_scan(
    db_session: AsyncSession, tmp_path: Path, *, filename: str, content: bytes
) -> Scan:
    (tmp_path / filename).write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename=filename,
            media_type=MediaType.IMAGE,
            storage_path=filename,
            mime_type="image/jpeg",
            size_bytes=len(content),
            sha256=sha256_of_bytes(content),
        )
    )
    service = ScanService(db_session)
    scan = await service.create_scan(media_id=media.id)
    await service.transition(scan, to=ScanStatus.VALIDATING)
    await service.transition(scan, to=ScanStatus.QUEUED)
    await db_session.commit()
    return scan


async def _reload(db_session: AsyncSession, scan_id: uuid.UUID) -> Scan:
    loaded = await ScanRepository(db_session).get(scan_id)
    assert loaded is not None
    return loaded


def _make_worker(tmp_path: Path) -> AnalysisWorker:
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=ScanExecutionService(
            registry=build_default_registry(),
            settings=Settings(media_storage_root=tmp_path),
        ),
        poll_interval=0.01,
    )


# --------------------------------------------------------------------------- #
# Registry + ordering
# --------------------------------------------------------------------------- #

def test_default_registry_has_metadata_registered() -> None:
    registry = build_default_registry()
    assert registry.names() == [
        "validate",
        "fingerprint",
        "metadata",
        "detect",
        "forensics",
        "xai",
        "evidence",
        "confidence",
        "risk",
        "verdict",
        "report",
    ]
    assert registry.get("metadata") is not None


def test_metadata_stage_order_matches_pipeline() -> None:
    registry = build_default_registry()
    assert [name for name in STAGE_ORDER if name in registry] == registry.names()


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

def test_jpeg_exif_values_extracted(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        make="Nikon",
        model="Z9",
        software="GIMP 2.10.30",
        orientation=6,
        date_time="2023:05:04 10:11:12",
        date_time_original="2023:05:04 10:11:12",
        iso=400,
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    assert payload["format"] == "JPEG"
    assert payload["exif"]["present"] is True
    assert payload["exif"]["camera_make"] == "Nikon"
    assert payload["exif"]["camera_model"] == "Z9"
    assert payload["exif"]["software"] == ["GIMP 2.10.30"]
    assert payload["exif"]["orientation"] == 6
    assert payload["exif"]["iso_speed_ratings"] == 400


def test_jpeg_without_exif_reports_absence(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes()))
    assert payload["exif"]["present"] is False
    assert payload["exif"]["camera_make"] is None
    assert payload["exif"]["software"] == []
    assert payload["presence"]["exif"] is False


def test_png_extraction(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _png_bytes(), mime_type="image/png"))
    assert payload["format"] == "PNG"
    assert payload["dimensions"] == {"width": 12, "height": 9}
    assert payload["exif"]["present"] is False


def test_gps_values_extracted(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        gps={
            "lat_ref": "N",
            "lat": [(37, 1), (47, 1), (300, 1)],
            "lon_ref": "W",
            "lon": [(122, 1), (25, 1), (0, 1)],
            "altitude": (125, 10),
            "date_stamp": "2023:05:04",
        }
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    assert payload["gps"]["present"] is True
    assert payload["gps"]["latitude"] == pytest.approx(37.8666667)
    assert payload["gps"]["longitude"] == pytest.approx(-122.4166667)
    assert payload["gps"]["altitude_m"] == pytest.approx(12.5)
    assert payload["gps"]["date_stamp"] == "2023:05:04"


def test_timestamp_normalized_to_naive_iso(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        date_time_original="2023:05:04 10:11:12", date_time="2023:05:04 10:11:12"
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    assert payload["exif"]["captured_at"] == "2023-05-04T10:11:12"
    assert payload["exif"]["modified_at"] == "2023-05-04T10:11:12"
    assert "Z" not in payload["exif"]["captured_at"]
    assert "+" not in payload["exif"]["captured_at"]


def test_xmp_values_extracted(tmp_path: Path) -> None:
    xmp = _xmp(
        "<xmp:CreatorTool>Adobe Photoshop 24.0</xmp:CreatorTool>"
        "<xmp:CreateDate>2023-05-04T10:11:12</xmp:CreateDate>"
        "<tiff:Software>Adobe Lightroom</tiff:Software>"
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(xmp=xmp)))
    assert payload["xmp"]["present"] is True
    assert payload["xmp"]["creator_tool"] == "Adobe Photoshop 24.0"
    assert payload["xmp"]["create_date"] == "2023-05-04T10:11:12"
    assert payload["xmp"]["software"] == ["Adobe Lightroom"]


def test_software_merged_deduplicated(tmp_path: Path) -> None:
    exif = build_exif_bytes(software="Adobe Photoshop 24.0")
    xmp = _xmp("<xmp:CreatorTool>Adobe Photoshop 24.0</xmp:CreatorTool>")
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif, xmp=xmp)))
    assert payload["software"] == ["Adobe Photoshop 24.0"]


def test_icc_presence_flag(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes()))
    assert payload["icc"]["present"] is False
    assert payload["presence"]["icc"] is False


# --------------------------------------------------------------------------- #
# Consistency analysis
# --------------------------------------------------------------------------- #

def test_editing_software_is_verified_evidence(tmp_path: Path) -> None:
    exif = build_exif_bytes(software="Adobe Photoshop 24.0")
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    finding = payload["consistency"]["findings"][0]
    assert finding["code"] == "editing_software_metadata"
    assert finding["evidence_type"] == "VERIFIED"
    assert "does not establish AI generation" in finding["message"]


def test_capture_later_than_modification_is_heuristic(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        date_time_original="2023:05:05 09:00:00", date_time="2023:05:04 09:00:00"
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    by_code = {f["code"]: f for f in payload["consistency"]["findings"]}
    assert "capture_later_than_modification" in by_code
    assert by_code["capture_later_than_modification"]["evidence_type"] == "HEURISTIC"


def test_out_of_range_orientation_is_verified_evidence(tmp_path: Path) -> None:
    exif = build_exif_bytes(orientation=99)
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    by_code = {f["code"]: f for f in payload["consistency"]["findings"]}
    assert by_code["exif_orientation_out_of_range"]["evidence_type"] == "VERIFIED"


def test_gps_presence_finding(tmp_path: Path) -> None:
    exif = build_exif_bytes(gps={"lat_ref": "N", "lat": [(10, 1), (0, 1), (0, 1)]})
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    codes = [f["code"] for f in payload["consistency"]["findings"]]
    assert "gps_present" in codes


def test_clean_file_has_no_findings(tmp_path: Path) -> None:
    exif = build_exif_bytes(make="Canon", model="EOS R5")
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    assert payload["consistency"]["findings"] == []
    assert payload["consistency"]["count"] == 0


def test_format_mime_mismatch_detected(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(), mime_type="image/png"))
    codes = [f["code"] for f in payload["consistency"]["findings"]]
    assert "format_mime_mismatch" in codes


# --------------------------------------------------------------------------- #
# Failure handling
# --------------------------------------------------------------------------- #

def test_stage_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="stored media file is missing"):
        asyncio.run(MetadataStage().run(_ctx(tmp_path, _media(storage_path="ghost.jpg"))))


def test_corrupt_image_fails_stage(tmp_path: Path) -> None:
    name = "corrupt.jpg"
    (tmp_path / name).write_bytes(b"this is definitely not a jpeg")
    with pytest.raises(StageError, match="not a readable image"):
        asyncio.run(MetadataStage().run(_ctx(tmp_path, _media(storage_path=name))))


def test_extraction_error_message_is_client_safe(tmp_path: Path) -> None:
    name = "broken.png"
    (tmp_path / name).write_bytes(b"\x89PNG\x0d\x0a\x1a\x0a" + b"truncated")
    with pytest.raises(MetadataExtractionError) as excinfo:
        extract_image_metadata(tmp_path / name)
    assert "/" not in excinfo.value.message
    assert tmp_path.name not in excinfo.value.message


def test_non_image_media_type_rejected(tmp_path: Path) -> None:
    media = Media(
        original_filename="clip.mp4",
        media_type=MediaType.VIDEO,
        storage_path="clip.mp4",
        mime_type="video/mp4",
    )
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(MetadataStage().run(_ctx(tmp_path, media)))


def test_malformed_metadata_does_not_fail_stage(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        date_time_original="not-a-date", date_time="not-a-date", orientation=99
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif)))
    assert payload["exif"]["captured_at"] is None
    assert payload["exif"]["modified_at"] is None
    assert any("unparseable datetime" in e for e in payload["extractor"]["errors"])
    assert payload["consistency"]["count"] >= 1


def test_malformed_xmp_is_recorded_not_fatal(tmp_path: Path) -> None:
    bad = b"<x:xmpmeta><rdf:RDF><rdf:Description<broken"
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(xmp=bad)))
    assert payload["xmp"]["present"] is False
    assert any(e.startswith("xmp:") for e in payload["extractor"]["errors"])


# --------------------------------------------------------------------------- #
# Result contract
# --------------------------------------------------------------------------- #

def test_result_ref_structure_and_provenance(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=build_exif_bytes())))
    assert set(payload) == {
        "format", "mode", "dimensions", "exif", "gps", "xmp", "icc", "presence",
        "software", "consistency", "provenance", "extractor",
    }
    assert payload["provenance"]["status"] == "UNAVAILABLE"
    assert "not implemented" in payload["provenance"]["note"]
    assert payload["extractor"]["library"] == "Pillow"


def test_no_fabricated_fields_when_metadata_absent(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _png_bytes(), mime_type="image/png"))
    assert payload["exif"]["camera_make"] is None
    assert payload["exif"]["captured_at"] is None
    assert payload["gps"]["latitude"] is None
    assert payload["xmp"]["creator_tool"] is None
    assert payload["software"] == []
    assert payload["consistency"]["findings"] == []


def test_all_findings_carry_known_evidence_types(tmp_path: Path) -> None:
    exif = build_exif_bytes(
        software="Adobe Photoshop 24.0",
        orientation=99,
        date_time_original="2023:05:05 09:00:00",
        date_time="2023:05:04 09:00:00",
        gps={"lat_ref": "N", "lat": [(10, 1), (0, 1), (0, 1)]},
    )
    payload = asyncio.run(_run_stage(tmp_path, _jpeg_bytes(exif=exif), mime_type="image/png"))
    for finding in payload["consistency"]["findings"]:
        assert finding["evidence_type"] in {
            "VERIFIED", "INFERENCE", "HEURISTIC", "UNKNOWN",
        }
    codes = {f["code"] for f in payload["consistency"]["findings"]}
    assert "exif_orientation_out_of_range" in codes
    assert "editing_software_metadata" in codes


def test_deterministic_result(tmp_path: Path) -> None:
    name = "det.jpg"
    (tmp_path / name).write_bytes(_jpeg_bytes(exif=build_exif_bytes(make="Nikon", software="GIMP")))
    stage, ctx = MetadataStage(), _ctx(tmp_path, _media(storage_path=name))
    first = asyncio.run(stage.run(ctx))
    second = asyncio.run(stage.run(ctx))
    assert first is not None and second is not None
    assert first.result_ref == second.result_ref


# --------------------------------------------------------------------------- #
# Pipeline integration
# --------------------------------------------------------------------------- #

async def test_worker_runs_metadata_stage_to_completed(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    exif = build_exif_bytes(make="Nikon", model="Z9", software="Adobe Photoshop 24.0")
    content = _jpeg_bytes(exif=exif)
    queued = await _queued_scan(db_session, tmp_path, filename="meta.jpg", content=content)
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 1

    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["metadata"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["metadata"].result_ref or "{}")
    assert payload["exif"]["camera_make"] == "Nikon"


async def test_worker_fails_scan_on_corrupt_stored_file(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(
        db_session, tmp_path, filename="broken.jpg", content=b"\xff\xd8\xff\xe0dead"
    )
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.FAILED
    assert "not a readable image" in (scan.error_message or "")
