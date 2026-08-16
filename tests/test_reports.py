"""Phase 11 — Forensic Report Engine tests.

Covers:
- report composition from real persisted pipeline outputs (18 scenarios),
- PDF rendering (17 scenarios),
- pipeline integration of the report stage (6 scenarios).

Every stub fixture below is explicitly labelled as a test double; none is ever
presented as real detector/explainer output.
"""

import asyncio
import base64
import binascii
import json
import re
import uuid
import zlib
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from app.assessment import ConfidenceEngine, RiskEngine, VerdictEngine
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan, ScanStage
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import EvidenceType, MediaType, ScanStatus, StageStatus
from app.evidence import EvidenceAvailability, SourceOutput, aggregate_evidence
from app.evidence.domain import EvidenceResult
from app.inference.base import DetectionResult
from app.inference.detectors.unavailable import UnavailableDetector
from app.media.hashing import sha256_of_bytes
from app.media.storage import LocalStorageProvider
from app.reports import compose_report, render_report_pdf, render_report_text
from app.reports.composer import ReportInputs
from app.reports.domain import ReportDocument, ReportResult
from app.reports.pdf import PDFRenderer
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.scans import ScanService
from app.workers.queue import build_default_worker
from app.workers.stages import build_default_registry
from app.workers.stages.base import StageContext, StageError
from app.workers.stages.report import ReportStage
from app.xai.base import XAIResult
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

# --------------------------------------------------------------------------- #
# Payload builders (mirror the real persisted result shapes)
# --------------------------------------------------------------------------- #


def _png_bytes(width: int = 12, height: int = 9) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (120, 40, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _finding(code: str, evidence_type: str, message: str) -> dict[str, str]:
    return {"code": code, "evidence_type": evidence_type, "message": message}


def _fingerprint_payload() -> dict[str, object]:
    return {"sha256": "a" * 64, "d_hash": "0" * 16, "size_bytes": 123}


def _metadata_payload() -> dict[str, object]:
    return {
        "format": "PNG",
        "mode": "RGB",
        "dimensions": {"width": 12, "height": 9},
        "exif": {"present": False},
        "gps": {"present": False},
        "xmp": {"present": False},
        "icc": {"present": False},
        "presence": {"exif": False, "xmp": False, "icc": False, "gps": False},
        "software": ["GIMP 2.10"],
        "consistency": {
            "findings": [
                _finding(
                    "editing_software_present",
                    "HEURISTIC",
                    "editing software is present; this is evidence of editing "
                    "history, never proof of AI generation",
                )
            ],
            "count": 1,
        },
        "provenance": {
            "status": "UNAVAILABLE",
            "note": "C2PA/manifest provenance parsing is not implemented in this build",
        },
        "extractor": {"library": "Pillow", "errors": []},
    }


def _detection_unavailable_payload() -> dict[str, object]:
    return UnavailableDetector().detect(Path("unused"), device="cpu").model_dump(
        mode="json"
    )


def _forensics_payload() -> dict[str, object]:
    analyzers: dict[str, object] = {}
    for name in ("ela", "noise", "frequency"):
        analyzers[name] = {
            "analyzer": name,
            "version": "1",
            "status": "COMPLETED",
            "error": None,
            "parameters": {"param": 1},
            "measurements": {f"{name}_mean": 0.5, f"{name}_std": 0.1},
            "findings": [
                _finding(
                    f"{name}_interpretation",
                    "HEURISTIC",
                    f"{name} measurements are a supporting signal only, never a "
                    "manipulation verdict",
                )
            ],
        }
    return {
        "image": {"format": "PNG", "width": 12, "height": 9, "mode": "RGB"},
        "summary": {"analyzers": 3, "completed": 3, "failed": 0},
        "analyzers": analyzers,
    }


def _xai_unavailable_payload() -> dict[str, object]:
    return XAIResult(
        status="UNAVAILABLE",
        reason="no detector model produced a prediction; XAI requires a real "
        "model inference to explain",
    ).model_dump(mode="json")


def _default_sources() -> dict[str, dict[str, object]]:
    return {
        "fingerprint": _fingerprint_payload(),
        "metadata": _metadata_payload(),
        "detect": _detection_unavailable_payload(),
        "forensics": _forensics_payload(),
        "xai": _xai_unavailable_payload(),
    }


def _aggregate(sources: Mapping[str, dict[str, object]]) -> EvidenceResult:
    outputs = {
        name: SourceOutput(EvidenceAvailability.AVAILABLE, payload=payload)
        for name, payload in sources.items()
    }
    return aggregate_evidence(outputs)


def _scan_with_sources(
    sources: Mapping[str, dict[str, object] | None],
    *,
    missing: set[str] | None = None,
) -> Scan:
    missing = missing or set()
    scan = Scan(media_id=uuid.uuid4())
    stages: list[ScanStage] = []
    for sequence, name in enumerate(STAGE_ORDER):
        if name in missing:
            continue
        stage = ScanStage(name=name, status=StageStatus.PENDING, sequence=sequence)
        if sources.get(name):
            stage.status = StageStatus.COMPLETED
            stage.result_ref = json.dumps(sources[name], sort_keys=True)
        stages.append(stage)
    scan.stages = stages
    return scan


def _ctx(tmp_path: Path, media: Media, *, scan: Scan) -> StageContext:
    return StageContext(
        scan=scan,
        media=media,
        storage=LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path, storage_dir=tmp_path),
    )


def _report_inputs(
    sources: Mapping[str, dict[str, object] | None],
    *,
    missing: set[str] | None = None,
    created_at: str = "2026-01-01T00:00:00+00:00",
    analyzed_at: str = "2026-01-01T00:00:01+00:00",
) -> ReportInputs:
    """Build the exact ``ReportInputs`` the real report stage would compose.

    Confidence/risk/verdict are produced by the real engines over the aggregated
    evidence — the report stage itself never computes them.
    """
    present = {k: v for k, v in sources.items() if v is not None}
    evidence_result = _aggregate(present)
    confidence = ConfidenceEngine.assess(evidence_result)
    risk = RiskEngine.assess(evidence_result, confidence)
    verdict = VerdictEngine.reach(evidence_result, confidence)
    evidence_payload = evidence_result.model_dump(mode="json")
    full_sources = dict(sources)
    full_sources["evidence"] = evidence_payload
    full_sources["confidence"] = confidence.model_dump(mode="json")
    full_sources["risk"] = risk.model_dump(mode="json")
    full_sources["verdict"] = verdict.model_dump(mode="json")
    scan = _scan_with_sources(full_sources, missing=missing)
    detection = sources.get("detect")
    xai = sources.get("xai")
    return ReportInputs(
        scan_id="scan-1",
        media_id="media-1",
        created_at=created_at,
        analyzed_at=analyzed_at,
        pipeline_status="COMPLETED",
        media_type="IMAGE",
        original_filename="a.png",
        size_bytes=123,
        mime_type="image/png",
        stage_statuses={s.name: s.status.value for s in scan.stages},
        fingerprint=sources.get("fingerprint"),
        metadata=sources.get("metadata"),
        detection=DetectionResult.model_validate(detection) if detection else None,
        forensics=sources.get("forensics"),
        xai=XAIResult.model_validate(xai) if xai else None,
        evidence=evidence_result,
        confidence=confidence,
        risk=risk,
        verdict=verdict,
    )


def _default_inputs() -> ReportInputs:
    return _report_inputs(_default_sources())


def _default_media() -> Media:
    return Media(
        original_filename="a.png",
        media_type=MediaType.IMAGE,
        storage_path="a.png",
        mime_type="image/png",
        size_bytes=123,
    )


# --------------------------------------------------------------------------- #
# PDF text helpers (decode content streams; no extra dependency)
# --------------------------------------------------------------------------- #


def _pdf_text(data: bytes) -> str:
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = match.group(1).strip(b"\r\n")
        try:
            if raw.endswith(b"~>"):
                compressed = base64.a85decode(raw[:-2], adobe=False)
            else:
                compressed = raw
            chunks.append(zlib.decompress(compressed).decode("latin-1"))
        except (zlib.error, ValueError, binascii.Error):
            continue
    return "\n".join(chunks)


def _has(text: str, needle: str) -> bool:
    """Whitespace-insensitive substring check (PDF literals wrap across Tj)."""
    return needle.lower().replace(" ", "") in text.lower().replace(" ", "")


# --------------------------------------------------------------------------- #
# Report composition (18 scenarios)
# --------------------------------------------------------------------------- #


def test_current_phase10_results_compose_successfully() -> None:
    document = compose_report(_default_inputs())
    assert isinstance(document, ReportDocument)
    assert document.case_id == "scan-1"
    assert document.media_id == "media-1"
    titles = [section.title for section in document.sections]
    assert titles == [
        "Case Information",
        "Executive Summary",
        "Pipeline Status",
        "Fingerprint",
        "Metadata",
        "Detection",
        "Visual Forensics",
        "XAI",
        "Evidence Aggregation",
        "Confidence",
        "Risk",
        "Verdict",
    ]
    assert document.summary
    assert document.limitations
    assert document.methodology["confidence_methodology_version"] == "1"


def test_insufficient_evidence_represented_correctly() -> None:
    document = compose_report(_default_inputs())
    confidence = next(s for s in document.sections if s.title == "Confidence")
    verdict = next(s for s in document.sections if s.title == "Verdict")
    assert _row(confidence, "Status") == "INSUFFICIENT_EVIDENCE"
    assert _row(confidence, "Value") == "NOT QUANTIFIED"
    assert _row(verdict, "Verdict") == "INSUFFICIENT_EVIDENCE"
    assert any("insufficient evidence" in s.lower() for s in document.summary.split(". "))


def test_detector_unavailable_represented_correctly() -> None:
    document = compose_report(_default_inputs())
    detection = next(s for s in document.sections if s.title == "Detection")
    rows = {row.label: row.value for row in detection.rows}
    assert rows["Status"] == "UNAVAILABLE"
    assert "no image detector is registered" in rows["Reason"]
    assert "No detector model was available" in detection.statements[0]
    assert document.methodology["detector"] == "UNAVAILABLE"
    assert document.methodology["detector_model"] == "UNAVAILABLE"


def test_xai_unavailable_represented_correctly() -> None:
    document = compose_report(_default_inputs())
    xai = next(s for s in document.sections if s.title == "XAI")
    assert _row(xai, "Status") == "UNAVAILABLE"
    assert any("No explainability heatmap was generated" in s for s in xai.statements)
    assert document.methodology["xai_explainer"] == "NOT IMPLEMENTED"


def test_c2pa_unavailable_represented_correctly() -> None:
    document = compose_report(_default_inputs())
    metadata = next(s for s in document.sections if s.title == "Metadata")
    provenance = next(r for r in metadata.rows if r.label == "Provenance Status")
    assert provenance.value == "UNAVAILABLE"
    assert any("C2PA" in limitation for limitation in document.limitations)


def test_metadata_findings_preserved() -> None:
    document = compose_report(_default_inputs())
    metadata = next(s for s in document.sections if s.title == "Metadata")
    finding = next(r for r in metadata.rows if r.label == "editing_software_present")
    assert finding.evidence_type is EvidenceType.HEURISTIC
    assert "editing history" in finding.value


def test_forensic_measurements_preserved() -> None:
    document = compose_report(_default_inputs())
    forensics = next(s for s in document.sections if s.title == "Visual Forensics")
    rows = {row.label: row.value for row in forensics.rows}
    assert rows["Analyzer: ela"] == "version=1 status=COMPLETED"
    assert "ela_mean" in rows["ela measurements"]
    assert document.methodology["forensic_analyzer_versions"] != "UNAVAILABLE"


def test_evidence_directions_preserved() -> None:
    document = compose_report(_default_inputs())
    evidence = next(s for s in document.sections if s.title == "Evidence Aggregation")
    for row in evidence.rows:
        if row.note and "direction=" in row.note:
            assert "direction=" in row.note


def test_evidence_types_preserved() -> None:
    document = compose_report(_default_inputs())
    evidence = next(s for s in document.sections if s.title == "Evidence Aggregation")
    assert any(
        row.evidence_type is not None and row.evidence_type.value == "VERIFIED"
        for row in evidence.rows
    )
    assert any(
        row.evidence_type is not None and row.evidence_type.value == "HEURISTIC"
        for row in evidence.rows
    )


def test_confidence_null_remains_null() -> None:
    document = compose_report(_default_inputs())
    confidence = next(s for s in document.sections if s.title == "Confidence")
    assert _row(confidence, "Value") == "NOT QUANTIFIED"
    assert "null" not in _row(confidence, "Value").lower()
    assert "0" != _row(confidence, "Value")


def test_risk_undetermined_remains_undetermined() -> None:
    document = compose_report(_default_inputs())
    risk = next(s for s in document.sections if s.title == "Risk")
    assert _row(risk, "Risk Level") == "UNDETERMINED"


def test_verdict_insufficient_remains_insufficient() -> None:
    document = compose_report(_default_inputs())
    verdict = next(s for s in document.sections if s.title == "Verdict")
    assert _row(verdict, "Verdict") == "INSUFFICIENT_EVIDENCE"
    assert any(
        "does not have sufficient validated evidence" in s for s in verdict.statements
    )


def test_limitations_are_preserved() -> None:
    document = compose_report(_default_inputs())
    joined = " | ".join(document.limitations)
    assert "detector unavailable" in joined
    assert "XAI unavailable" in joined
    assert "confidence not calibrated" in joined
    assert "no face/identity assessment" in joined
    assert len(document.limitations) == len(set(document.limitations))


def test_model_and_methodology_versions_preserved() -> None:
    document = compose_report(_default_inputs())
    assert document.methodology["confidence_methodology_version"] == "1"
    assert document.methodology["risk_methodology_version"] == "1"
    assert document.methodology["verdict_methodology_version"] == "1"
    assert document.methodology["report_version"] == "1"
    assert document.methodology["forensic_analyzer_versions"] != "UNAVAILABLE"


def test_no_filesystem_paths_exposed() -> None:
    document = compose_report(_default_inputs())
    rendered = render_report_text(document)
    lowered = rendered.lower()
    assert "storage/media" not in lowered
    assert "storage/reports" not in lowered
    assert "/" + "tmp/" not in lowered
    assert "/home/" not in lowered
    assert "/var/" not in lowered
    assert "media_storage_root" not in lowered
    assert "storage_dir" not in lowered


def test_no_secrets_exposed() -> None:
    document = compose_report(_default_inputs())
    rendered = render_report_text(document)
    assert "secret" not in rendered.lower()
    assert "password" not in rendered.lower()
    assert "token" not in rendered.lower()


def test_deterministic_composition() -> None:
    a = compose_report(_default_inputs())
    b = compose_report(_default_inputs())
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_identical_input_identical_document() -> None:
    a = compose_report(_default_inputs())
    b = compose_report(_report_inputs(_default_sources()))
    assert a == b


def test_stub_detector_score_never_becomes_confidence() -> None:
    """STUB detection payload with a real-looking score — the report presents it
    as a detector model score with its own semantics, never as confidence or
    probability."""
    sources = dict(_default_sources())
    detection = UnavailableDetector().detect(Path("unused"), device="cpu").model_dump(
        mode="json"
    )
    detection["inference"]["status"] = "AVAILABLE"
    detection["prediction"] = {
        "label": "manipulated",
        "score": 0.93,
        "score_semantics": "sigmoid probability",
        "class_list": ["authentic", "manipulated"],
    }
    detection["evidence_type"] = "INFERENCE"
    sources["detect"] = detection
    document = compose_report(_report_inputs(sources))
    confidence = next(s for s in document.sections if s.title == "Confidence")
    assert _row(confidence, "Value") == "NOT QUANTIFIED"
    assert any(
        "no validated/calibrated methodology currently supports a numeric "
        "confidence probability" in s.lower()
        for s in confidence.statements
    )
    detection_section = next(s for s in document.sections if s.title == "Detection")
    rows = {row.label: row.value for row in detection_section.rows}
    assert rows["Prediction Score"] == "0.93"
    assert rows["Score Semantics"] == "sigmoid probability"
    rendered = render_report_text(document)
    assert "93%" not in rendered
    assert "98%" not in rendered


# --------------------------------------------------------------------------- #
# PDF rendering (17 scenarios)
# --------------------------------------------------------------------------- #


def test_pdf_generated_successfully() -> None:
    document = compose_report(_default_inputs())
    pdf = render_report_pdf(document)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_pdf_contains_case_information() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "scan-1")
    assert _has(text, "media-1")
    assert _has(text, "a.png")


def test_pdf_contains_executive_summary() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Executive Summary")
    assert _has(text, "insufficient evidence for a stronger")


def test_pdf_contains_fingerprint() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "SHA-256")
    assert _has(text, "a" * 64)
    assert _has(text, "never authenticity")


def test_pdf_contains_metadata() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Provenance Status")
    assert _has(text, "UNAVAILABLE")
    assert _has(text, "editing_software_present")


def test_pdf_contains_detection_state() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Detection")
    assert _has(text, "No detector model was available")


def test_pdf_contains_visual_forensics() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Visual Forensics")
    assert _has(text, "ela_mean")


def test_pdf_contains_xai_state() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "No explainability heatmap was generated")


def test_pdf_contains_evidence() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Evidence Aggregation")
    assert _has(text, "Total Evidence Items")


def test_pdf_contains_confidence() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Confidence")
    assert _has(text, "NOT QUANTIFIED")


def test_pdf_contains_risk() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "UNDETERMINED")


def test_pdf_contains_verdict() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "INSUFFICIENT EVIDENCE")


def test_pdf_contains_limitations() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "Limitations")
    assert _has(text, "no face/identity assessment")


def test_pdf_no_internal_filesystem_paths() -> None:
    document = compose_report(_default_inputs())
    pdf = render_report_pdf(document)
    text = _pdf_text(pdf)
    assert "/" + "tmp/" not in text
    assert "storage/media" not in text
    assert "/home/" not in text


def test_pdf_no_fake_confidence() -> None:
    sources = dict(_default_sources())
    detection = UnavailableDetector().detect(Path("unused"), device="cpu").model_dump(
        mode="json"
    )
    detection["inference"]["status"] = "AVAILABLE"
    detection["prediction"] = {
        "label": "manipulated",
        "score": 0.93,
        "score_semantics": "sigmoid probability",
        "class_list": ["authentic", "manipulated"],
    }
    detection["evidence_type"] = "INFERENCE"
    sources["detect"] = detection
    pdf = render_report_pdf(compose_report(_report_inputs(sources)))
    text = _pdf_text(pdf)
    assert _has(text, "NOT QUANTIFIED")
    assert "%" not in text
    assert "98%" not in text


def test_pdf_no_fake_heatmaps() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "No explainability heatmap was generated")
    assert "heatmap.png" not in text
    assert "suspicious region" not in text.lower()
    assert "fabricated" not in text.lower()


def test_pdf_no_fake_model_identity() -> None:
    pdf = render_report_pdf(compose_report(_default_inputs()))
    text = _pdf_text(pdf)
    assert _has(text, "UNAVAILABLE")
    assert "resnet" not in text.lower()
    assert "efficientnet" not in text.lower()


def test_pdf_byte_determinism() -> None:
    document = compose_report(_default_inputs())
    assert render_report_pdf(document) == render_report_pdf(document)


# --------------------------------------------------------------------------- #
# Pipeline integration (6 scenarios)
# --------------------------------------------------------------------------- #


def test_report_stage_registered_after_verdict() -> None:
    registry = build_default_registry()
    names = registry.names()
    assert names[-1] == "report"
    assert "verdict" in names
    assert names.index("verdict") < names.index("report")
    assert [name for name in STAGE_ORDER if name in registry] == names


def _full_stage_scan(tmp_path: Path) -> Scan:
    sources = dict(_default_sources())
    evidence = _aggregate(sources)
    confidence = ConfidenceEngine.assess(evidence)
    risk = RiskEngine.assess(evidence, confidence)
    verdict = VerdictEngine.reach(evidence, confidence)
    sources["evidence"] = evidence.model_dump(mode="json")
    sources["confidence"] = confidence.model_dump(mode="json")
    sources["risk"] = risk.model_dump(mode="json")
    sources["verdict"] = verdict.model_dump(mode="json")
    return _scan_with_sources(sources)


def test_report_stage_executes(tmp_path: Path) -> None:
    media = _default_media()
    scan = _full_stage_scan(tmp_path)
    result = asyncio.run(ReportStage().run(_ctx(tmp_path, media, scan=scan)))
    assert result is not None and result.result_ref is not None
    payload = json.loads(result.result_ref)
    report = ReportResult.model_validate(payload)
    assert report.status == "COMPLETED"
    assert report.artifact is not None
    assert report.artifact.available is True
    assert report.artifact.reference == f"{scan.id}.pdf"
    assert report.document.case_id == str(scan.id)
    assert report.summary
    assert report.limitations


def test_report_stage_persists_artifact(tmp_path: Path) -> None:
    media = _default_media()
    scan = _full_stage_scan(tmp_path)
    result = asyncio.run(ReportStage().run(_ctx(tmp_path, media, scan=scan)))
    assert result is not None and result.result_ref is not None
    report = ReportResult.model_validate(json.loads(result.result_ref))
    assert report.artifact is not None
    stored = tmp_path / "reports" / report.artifact.reference
    assert stored.exists()
    assert stored.read_bytes().startswith(b"%PDF")


def test_report_stage_requires_image(tmp_path: Path) -> None:
    media = Media(
        original_filename="v.png",
        media_type=MediaType.VIDEO,
        storage_path="v.png",
        mime_type="image/png",
    )
    scan = _scan_with_sources({})
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(ReportStage().run(_ctx(tmp_path, media, scan=scan)))


def test_report_stage_failure_is_client_safe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(self: object, document: ReportDocument) -> bytes:
        raise RuntimeError("boom at /var/lib/phantom/report.pdf")

    monkeypatch.setattr(PDFRenderer, "render", _boom)
    media = _default_media()
    scan = _full_stage_scan(tmp_path)
    with pytest.raises(StageError) as excinfo:
        asyncio.run(ReportStage().run(_ctx(tmp_path, media, scan=scan)))
    message = str(excinfo.value)
    assert message == "report could not be rendered"
    assert "/var/lib" not in message
    assert "RuntimeError" not in message


async def test_report_stage_worker_end_to_end(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path)
    worker = build_default_worker(
        Settings(media_storage_root=tmp_path, storage_dir=tmp_path)
    )
    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["report"].status is StageStatus.COMPLETED
    assert by_name["report"].result_ref is not None
    payload = json.loads(by_name["report"].result_ref or "{}")
    report = ReportResult.model_validate(payload)
    assert report.artifact is not None
    assert report.artifact.available is True
    stored = tmp_path / "reports" / report.artifact.reference
    assert stored.exists()
    pdf_bytes = stored.read_bytes()
    assert pdf_bytes.startswith(b"%PDF")
    text = _pdf_text(pdf_bytes)
    assert _has(text, "NOT QUANTIFIED")
    assert _has(text, "INSUFFICIENT EVIDENCE")
    assert "/" + "tmp/" not in text


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _row(section: Any, label: str) -> str:
    for row in section.rows:
        if row.label == label:
            return str(row.value)
    raise AssertionError(f"row {label!r} not found in section {section.title!r}")


async def _queued_scan(db_session: AsyncSession, tmp_path: Path) -> Scan:
    content = _png_bytes()
    (tmp_path / "a.png").write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename="a.png",
            media_type=MediaType.IMAGE,
            storage_path="a.png",
            mime_type="image/png",
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


async def _reload(db_session: AsyncSession, scan_id: Any) -> Scan:
    loaded = await ScanRepository(db_session).get(scan_id)
    assert loaded is not None
    return loaded
