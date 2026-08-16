"""Evidence aggregation tests (domain, normalization, aggregation, pipeline).

Uses controlled stub detectors for detection results. The evidence engine must
never invent evidence, never treat UNAVAILABLE as a negative signal, and never
emit a numeric confidence — those are the core scientific-honesty guarantees
under test here.
"""

import asyncio
import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan, ScanStage
from app.db.session import SessionFactory
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import (
    EvidenceType,
    MediaType,
    ScanStatus,
    StageStatus,
)
from app.evidence import (
    ConfidenceStatus,
    EvidenceAvailability,
    EvidenceCategory,
    EvidenceDirection,
    EvidenceItem,
    EvidenceResult,
    EvidenceSource,
    SourceOutput,
    aggregate_evidence,
    normalize_source,
)
from app.inference.base import (
    DetectionPrediction,
    DetectionResult,
    DetectorIdentity,
    InferenceSummary,
)
from app.inference.detectors.unavailable import UnavailableDetector
from app.media.hashing import sha256_of_bytes
from app.media.storage import LocalStorageProvider
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.execution import ScanExecutionService
from app.services.scans import ScanService
from app.workers.queue import AnalysisWorker
from app.workers.registry import StageRegistry
from app.workers.stages.base import StageContext, StageError
from app.workers.stages.detect import DetectionStage
from app.workers.stages.evidence import EvidenceAggregationStage
from app.workers.stages.fingerprint import FingerprintStage
from app.workers.stages.forensics import VisualForensicsStage
from app.workers.stages.metadata import MetadataStage
from app.workers.stages.validate import ValidateStage
from app.workers.stages.xai import XAIStage
from app.xai.base import XAIHeatmap, XAIInterpretation, XAIResult
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

# --------------------------------------------------------------------------- #
# Payload builders (mirror the real persisted result shapes)
# --------------------------------------------------------------------------- #

def _fingerprint_payload(
    *,
    sha256: str = "a" * 64,
    d_hash: str = "0" * 16,
    size_bytes: int = 123,
) -> dict[str, Any]:
    return {"sha256": sha256, "d_hash": d_hash, "size_bytes": size_bytes}


def _finding(code: str, evidence_type: str, message: str) -> dict[str, str]:
    return {"code": code, "evidence_type": evidence_type, "message": message}


def _metadata_payload(
    *,
    presence: dict[str, bool] | None = None,
    software: list[str] | None = None,
    findings: list[dict[str, str]] | None = None,
    provenance_unavailable: bool = True,
) -> dict[str, Any]:
    return {
        "format": "PNG",
        "mode": "RGB",
        "dimensions": {"width": 12, "height": 9},
        "exif": {"present": presence.get("exif", False) if presence else False},
        "gps": {"present": presence.get("gps", False) if presence else False},
        "xmp": {"present": presence.get("xmp", False) if presence else False},
        "icc": {"present": presence.get("icc", False) if presence else False},
        "presence": (
            presence
            or {"exif": False, "xmp": False, "icc": False, "gps": False}
        ),
        "software": software or [],
        "consistency": {
            "findings": findings or [],
            "count": len(findings or []),
        },
        "provenance": (
            {
                "status": "UNAVAILABLE",
                "note": "C2PA/manifest provenance parsing is not implemented in this build",
            }
            if provenance_unavailable
            else {"status": "AVAILABLE", "note": None}
        ),
        "extractor": {"library": "Pillow", "errors": []},
    }


def _detection_unavailable_payload() -> dict[str, Any]:
    return UnavailableDetector().detect(Path("unused"), device="cpu").model_dump(
        mode="json"
    )


def _stub_detection_payload(
    *, label: str = "FAKE", score: float = 0.87
) -> dict[str, Any]:
    result = DetectionResult(
        detector=DetectorIdentity(
            name="stub-image",
            model_name="stub-model",
            model_version="0.0.1",
            checkpoint_sha256="b" * 64,
            preprocessing_version="pre-1",
        ),
        media_type=MediaType.IMAGE,
        prediction=DetectionPrediction(
            label=label,
            score=score,
            score_semantics="sigmoid probability",
            class_list=("REAL", "FAKE"),
        ),
        inference=InferenceSummary(status="AVAILABLE", device="cpu"),
        evidence_type=EvidenceType.INFERENCE,
    )
    return result.model_dump(mode="json")


def _forensics_payload(
    *,
    completed: tuple[str, ...] = ("ela", "noise", "frequency"),
    failed: tuple[str, ...] = (),
) -> dict[str, Any]:
    analyzers: dict[str, Any] = {}
    for name in completed:
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
    for name in failed:
        analyzers[name] = {
            "analyzer": name,
            "version": "1",
            "status": "FAILED",
            "error": "simulated analyzer failure",
            "parameters": {},
            "measurements": {},
            "findings": [],
        }
    return {
        "image": {"format": "PNG", "width": 12, "height": 9, "mode": "RGB"},
        "summary": {
            "analyzers": len(analyzers),
            "completed": len(completed),
            "failed": len(failed),
        },
        "analyzers": analyzers,
    }


def _xai_unavailable_payload() -> dict[str, Any]:
    return XAIResult(
        status="UNAVAILABLE",
        reason="no detector model produced a prediction; XAI requires a real "
        "model inference to explain",
    ).model_dump(mode="json")


def _xai_completed_payload() -> dict[str, Any]:
    return XAIResult(
        status="COMPLETED",
        explainer=dict(name="stub-gradcam", version="1", technique="grad-cam"),
        model=dict(
            name="stub-model", version="0.0.1", checkpoint_sha256="b" * 64
        ),
        heatmap=XAIHeatmap(
            available=True, format="png", width=12, height=9, reference="h.png"
        ),
        interpretation=XAIInterpretation(
            target_label="FAKE",
            target_score=0.87,
            score_semantics="sigmoid probability",
            summary="stub explanation",
            limitation="stub only",
        ),
    ).model_dump(mode="json")


def _default_sources() -> dict[str, dict[str, Any]]:
    return {
        "fingerprint": _fingerprint_payload(),
        "metadata": _metadata_payload(),
        "detect": _detection_unavailable_payload(),
        "forensics": _forensics_payload(),
        "xai": _xai_unavailable_payload(),
    }


def _aggregate(sources: dict[str, dict[str, Any]]) -> EvidenceResult:
    outputs = {
        name: SourceOutput(
            EvidenceAvailability.AVAILABLE, payload=payload
        )
        for name, payload in sources.items()
    }
    return aggregate_evidence(outputs)


# --------------------------------------------------------------------------- #
# Domain / contract
# --------------------------------------------------------------------------- #

def test_evidence_source_enum_values() -> None:
    assert EvidenceSource.FINGERPRINT == "FINGERPRINT"
    assert EvidenceSource.METADATA == "METADATA"
    assert EvidenceSource.DETECTION == "DETECTION"
    assert EvidenceSource.VISUAL_FORENSICS == "VISUAL_FORENSICS"
    assert EvidenceSource.XAI == "XAI"


def test_evidence_item_requires_fields() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(observation="x")  # type: ignore[call-arg]
    item = EvidenceItem(
        code="c",
        source=EvidenceSource.METADATA,
        category=EvidenceCategory.PROVENANCE,
        evidence_type=EvidenceType.VERIFIED,
        observation="o",
        interpretation="i",
    )
    assert item.direction is EvidenceDirection.NEUTRAL


def test_no_manipulation_category_exists() -> None:
    assert not any(c.value == "MANIPULATION" for c in EvidenceCategory)


def test_evidence_type_is_shared_taxonomy() -> None:
    assert EvidenceItem(
        code="c",
        source=EvidenceSource.METADATA,
        category=EvidenceCategory.PROVENANCE,
        evidence_type=EvidenceType.VERIFIED,
        observation="o",
        interpretation="i",
    ).evidence_type is EvidenceType.VERIFIED


def test_confidence_statuses() -> None:
    assert ConfidenceStatus.INSUFFICIENT_EVIDENCE == "INSUFFICIENT_EVIDENCE"
    assert ConfidenceStatus.SUFFICIENT_EVIDENCE == "SUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------- #
# Aggregation: availability + confidence (honest, no fabrication)
# --------------------------------------------------------------------------- #

def test_empty_sources_all_unavailable_confidence_insufficient() -> None:
    result = _aggregate({})
    assert result.status == "COMPLETED"
    assert result.evidence == []
    assert result.summary.total == 0
    assert result.summary.independent_count == 0
    assert result.confidence.status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert result.confidence.value is None
    for source in EvidenceSource:
        assert result.availability[source] is EvidenceAvailability.UNAVAILABLE


def test_confidence_insufficient_even_with_all_evidence_available() -> None:
    result = _aggregate(_default_sources())
    assert result.confidence.status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert result.confidence.value is None
    assert "not the probability" in result.confidence.semantics
    assert any("fabricated" in reason for reason in result.confidence.reasons)


def test_confidence_reasons_list_unavailable_sources() -> None:
    sources = _default_sources()
    del sources["detect"]
    del sources["xai"]
    result = _aggregate(sources)
    joined = " ".join(result.confidence.reasons)
    assert "DETECTION evidence is unavailable" in joined
    assert "XAI evidence is unavailable" in joined


def test_availability_map_records_all_sources() -> None:
    result = _aggregate(_default_sources())
    assert set(result.availability) == set(EvidenceSource)
    assert result.availability[EvidenceSource.FINGERPRINT] is EvidenceAvailability.AVAILABLE
    assert result.availability[EvidenceSource.METADATA] is EvidenceAvailability.AVAILABLE
    assert result.availability[EvidenceSource.DETECTION] is EvidenceAvailability.UNAVAILABLE
    assert (
        result.availability[EvidenceSource.VISUAL_FORENSICS]
        is EvidenceAvailability.AVAILABLE
    )
    assert result.availability[EvidenceSource.XAI] is EvidenceAvailability.UNAVAILABLE


def test_unavailable_detection_is_not_negative_evidence() -> None:
    result = _aggregate(_default_sources())
    codes = {item.code for item in result.evidence}
    assert "detection.prediction" not in codes
    assert result.summary.by_direction["NEUTRAL"] == result.summary.total
    assert "SUPPORTING_SYNTHETIC" not in result.summary.by_direction
    assert "SUPPORTING_AUTHENTICITY" not in result.summary.by_direction


def test_aggregation_is_deterministic() -> None:
    sources = _default_sources()
    first = _aggregate(sources).model_dump(mode="json")
    second = _aggregate(sources).model_dump(mode="json")
    assert first == second


def test_summary_counts() -> None:
    result = _aggregate(_default_sources())
    assert result.summary.total == len(result.evidence)
    assert result.summary.independent_count <= result.summary.total
    assert result.summary.by_evidence_type["VERIFIED"] >= 1
    assert result.summary.by_evidence_type["HEURISTIC"] >= 1
    assert "INFERENCE" not in result.summary.by_evidence_type


# --------------------------------------------------------------------------- #
# Normalization: fingerprint
# --------------------------------------------------------------------------- #

def test_fingerprint_sha256_evidence() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.FINGERPRINT, _fingerprint_payload()
    )
    assert availability is EvidenceAvailability.AVAILABLE
    sha = next(i for i in items if i.code == "fingerprint.sha256")
    assert sha.evidence_type is EvidenceType.VERIFIED
    assert sha.category is EvidenceCategory.FILE_INTEGRITY
    assert sha.direction is EvidenceDirection.NEUTRAL
    assert sha.details is not None and sha.details["sha256"] == "a" * 64


def test_fingerprint_dhash_is_heuristic() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.FINGERPRINT, _fingerprint_payload()
    )
    dhash = next(i for i in items if i.code == "fingerprint.dhash")
    assert dhash.evidence_type is EvidenceType.HEURISTIC
    assert dhash.direction is EvidenceDirection.NEUTRAL


def test_fingerprint_empty_payload_unavailable() -> None:
    _, availability, limitations = normalize_source(
        EvidenceSource.FINGERPRINT, {}
    )
    assert availability is EvidenceAvailability.UNAVAILABLE
    assert limitations


# --------------------------------------------------------------------------- #
# Normalization: metadata
# --------------------------------------------------------------------------- #

def test_metadata_presence_observations_neutral() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            presence={"exif": True, "xmp": True, "icc": False, "gps": False}
        ),
    )
    assert availability is EvidenceAvailability.AVAILABLE
    codes = {i.code: i for i in items}
    assert codes["metadata.exif_present"].evidence_type is EvidenceType.VERIFIED
    assert codes["metadata.exif_present"].direction is EvidenceDirection.NEUTRAL
    assert codes["metadata.icc_absent"].direction is EvidenceDirection.NEUTRAL


def test_metadata_absence_is_not_ai_evidence() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(presence={"exif": False, "xmp": False, "icc": False, "gps": False}),
    )
    absent = next(i for i in items if i.code == "metadata.exif_absent")
    assert "not evidence of AI generation" in absent.interpretation
    assert absent.direction is EvidenceDirection.NEUTRAL


def test_metadata_software_present_neutral() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(software=["Adobe Photoshop"]),
    )
    software = next(i for i in items if i.code == "metadata.software_present")
    assert software.direction is EvidenceDirection.NEUTRAL
    assert "not evidence of AI generation" in software.interpretation


def test_metadata_editing_software_finding_editing_history() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            findings=[
                _finding(
                    "editing_software_metadata",
                    "VERIFIED",
                    "software metadata indicates processing by Adobe Photoshop; "
                    "this does not establish AI generation",
                )
            ]
        ),
    )
    item = next(i for i in items if i.code == "metadata.editing_software_metadata")
    assert item.direction is EvidenceDirection.SUPPORTING_EDITING_HISTORY
    assert item.category is EvidenceCategory.PROVENANCE
    assert item.evidence_type is EvidenceType.VERIFIED


def test_metadata_timestamp_inconsistency_heuristic_not_manipulation() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            findings=[
                _finding(
                    "capture_later_than_modification",
                    "HEURISTIC",
                    "EXIF capture timestamp is later than the EXIF modification "
                    "timestamp",
                )
            ]
        ),
    )
    item = next(
        i for i in items if i.code == "metadata.capture_later_than_modification"
    )
    assert item.evidence_type is EvidenceType.HEURISTIC
    assert item.direction is EvidenceDirection.SUPPORTING_EDITING_HISTORY
    assert "does not establish manipulation" in item.interpretation


def test_metadata_gps_present_neutral_not_authenticity() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            presence={"exif": True, "xmp": False, "icc": False, "gps": True},
            findings=[
                _finding(
                    "gps_present",
                    "VERIFIED",
                    "GPS coordinates are present in the metadata (privacy-sensitive)",
                )
            ],
        ),
    )
    gps = next(i for i in items if i.code == "metadata.gps_present")
    assert gps.direction is EvidenceDirection.NEUTRAL
    assert gps.category is EvidenceCategory.PROVENANCE


def test_metadata_format_mime_mismatch_neutral() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            findings=[
                _finding(
                    "format_mime_mismatch",
                    "VERIFIED",
                    "detected image format PNG does not match the recorded mime type image/jpeg",
                )
            ]
        ),
    )
    mismatch = next(i for i in items if i.code == "metadata.format_mime_mismatch")
    assert mismatch.evidence_type is EvidenceType.VERIFIED
    assert mismatch.direction is EvidenceDirection.NEUTRAL


def test_metadata_unknown_finding_code_stays_neutral() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(
            findings=[_finding("future_code", "HEURISTIC", "some future finding")]
        ),
    )
    item = next(i for i in items if i.code == "metadata.future_code")
    assert item.direction is EvidenceDirection.NEUTRAL
    assert item.category is EvidenceCategory.METADATA_CONSISTENCY


def test_metadata_provenance_unavailable_is_limitation_not_source_failure() -> None:
    items, availability, limitations = normalize_source(
        EvidenceSource.METADATA,
        _metadata_payload(provenance_unavailable=True),
    )
    assert availability is EvidenceAvailability.AVAILABLE
    assert any("C2PA provenance is unavailable" in note for note in limitations)


# --------------------------------------------------------------------------- #
# Normalization: detection
# --------------------------------------------------------------------------- #

def test_detection_unavailable_produces_no_evidence() -> None:
    items, availability, limitations = normalize_source(
        EvidenceSource.DETECTION, _detection_unavailable_payload()
    )
    assert items == ()
    assert availability is EvidenceAvailability.UNAVAILABLE
    assert limitations


def test_detection_real_prediction_inference_evidence() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.DETECTION, _stub_detection_payload()
    )
    assert availability is EvidenceAvailability.AVAILABLE
    item = items[0]
    assert item.code == "detection.prediction"
    assert item.evidence_type is EvidenceType.INFERENCE
    assert item.category is EvidenceCategory.SYNTHETIC_GENERATION
    assert item.direction is EvidenceDirection.SUPPORTING_SYNTHETIC
    assert item.details is not None
    assert item.details["model_name"] == "stub-model"
    assert item.details["model_version"] == "0.0.1"
    assert item.details["checkpoint_sha256"] == "b" * 64
    assert item.details["score"] == 0.87
    assert item.details["score_semantics"] == "sigmoid probability"
    assert item.correlation_group == "model-inference"


def test_detection_real_label_real_maps_authenticity() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.DETECTION, _stub_detection_payload(label="REAL", score=0.6)
    )
    item = items[0]
    assert item.category is EvidenceCategory.AUTHENTICITY
    assert item.direction is EvidenceDirection.SUPPORTING_AUTHENTICITY


def test_detection_without_inference_classification_is_unavailable() -> None:
    payload = _stub_detection_payload()
    payload["evidence_type"] = None
    _, availability, _ = normalize_source(EvidenceSource.DETECTION, payload)
    assert availability is EvidenceAvailability.UNAVAILABLE


# --------------------------------------------------------------------------- #
# Normalization: forensics
# --------------------------------------------------------------------------- #

def test_forensics_completed_measurements_neutral() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.VISUAL_FORENSICS, _forensics_payload()
    )
    assert availability is EvidenceAvailability.AVAILABLE
    assert {i.code for i in items} == {
        "forensics.ela", "forensics.noise", "forensics.frequency",
    }
    for item in items:
        assert item.evidence_type is EvidenceType.VERIFIED
        assert item.category is EvidenceCategory.VISUAL_ANOMALY
        assert item.direction is EvidenceDirection.NEUTRAL


def test_forensics_never_yields_manipulation_direction() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.VISUAL_FORENSICS, _forensics_payload()
    )
    assert all(
        item.direction is EvidenceDirection.NEUTRAL for item in items
    )
    assert EvidenceDirection.SUPPORTING_MANIPULATION not in {
        item.direction for item in items
    }


def test_forensics_uses_heuristic_interpretation_from_payload() -> None:
    items, _, _ = normalize_source(
        EvidenceSource.VISUAL_FORENSICS, _forensics_payload()
    )
    ela = next(i for i in items if i.code == "forensics.ela")
    assert "supporting signal only" in ela.interpretation


def test_forensics_partial_failure_still_available() -> None:
    items, availability, limitations = normalize_source(
        EvidenceSource.VISUAL_FORENSICS,
        _forensics_payload(completed=("noise",), failed=("ela", "frequency")),
    )
    assert availability is EvidenceAvailability.AVAILABLE
    assert len(items) == 1
    assert any("ela failed" in note for note in limitations)


def test_forensics_all_failed_is_failed_not_evidence() -> None:
    items, availability, limitations = normalize_source(
        EvidenceSource.VISUAL_FORENSICS,
        _forensics_payload(completed=(), failed=("ela", "noise", "frequency")),
    )
    assert items == ()
    assert availability is EvidenceAvailability.FAILED
    assert limitations


# --------------------------------------------------------------------------- #
# Normalization: xai
# --------------------------------------------------------------------------- #

def test_xai_unavailable_produces_no_evidence() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.XAI, _xai_unavailable_payload()
    )
    assert items == ()
    assert availability is EvidenceAvailability.UNAVAILABLE


def test_xai_completed_is_model_behavior_evidence() -> None:
    items, availability, _ = normalize_source(
        EvidenceSource.XAI, _xai_completed_payload()
    )
    assert availability is EvidenceAvailability.AVAILABLE
    item = items[0]
    assert item.code == "xai.explanation"
    assert item.evidence_type is EvidenceType.INFERENCE
    assert item.category is EvidenceCategory.MODEL_BEHAVIOR
    assert item.direction is EvidenceDirection.NEUTRAL
    assert item.correlation_group == "model-inference"
    assert "not ground-truth evidence" in item.interpretation


# --------------------------------------------------------------------------- #
# Correlation handling (independence)
# --------------------------------------------------------------------------- #

def test_correlation_visual_compression_deduped() -> None:
    sources = _default_sources()
    sources["forensics"] = _forensics_payload()
    result = _aggregate(sources)
    assert "visual-compression" in result.correlation.groups
    assert result.summary.by_category["VISUAL_ANOMALY"] == 3
    assert result.summary.independent_count < result.summary.total


def test_correlation_xai_not_independent_of_detection() -> None:
    sources = _default_sources()
    sources["detect"] = _stub_detection_payload()
    sources["xai"] = _xai_completed_payload()
    result = _aggregate(sources)
    assert "model-inference" in result.correlation.groups
    detection = next(i for i in result.evidence if i.code == "detection.prediction")
    xai = next(i for i in result.evidence if i.code == "xai.explanation")
    assert detection in result.evidence
    assert xai in result.evidence
    assert result.summary.total == 11
    assert result.summary.total - result.summary.independent_count == 2


def test_correlation_note_documented() -> None:
    result = _aggregate(_default_sources())
    assert result.correlation.note
    assert "never treated as fully independent" in result.correlation.note


# --------------------------------------------------------------------------- #
# Evidence stage
# --------------------------------------------------------------------------- #

def _png_bytes(width: int = 12, height: int = 9) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (120, 40, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _scan_with_sources(
    sources: dict[str, dict[str, Any] | None],
    *,
    failed: set[str] | None = None,
    missing: set[str] | None = None,
) -> Scan:
    failed = failed or set()
    missing = missing or set()
    scan = Scan(media_id=uuid.uuid4())
    stages: list[ScanStage] = []
    for sequence, name in enumerate(STAGE_ORDER):
        if name in missing:
            continue
        stage = ScanStage(name=name, status=StageStatus.PENDING, sequence=sequence)
        if name in failed:
            stage.status = StageStatus.FAILED
            stage.error_message = "simulated failure"
        elif sources.get(name):
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
        settings=Settings(media_storage_root=tmp_path, detection_device="cpu"),
    )


async def _run_stage(
    tmp_path: Path,
    sources: dict[str, dict[str, Any] | None],
    *,
    failed: set[str] | None = None,
    missing: set[str] | None = None,
    media_type: MediaType = MediaType.IMAGE,
    storage_path: str | None = None,
) -> dict[str, Any]:
    name = storage_path or f"evidence-{uuid.uuid4().hex}.png"
    media = Media(
        original_filename=name,
        media_type=media_type,
        storage_path=name,
        mime_type="image/png",
    )
    scan = _scan_with_sources(sources, failed=failed, missing=missing)
    stage = EvidenceAggregationStage()
    result = await stage.run(_ctx(tmp_path, media, scan=scan))
    assert result is not None and result.result_ref is not None
    parsed = json.loads(result.result_ref)
    assert isinstance(parsed, dict)
    return parsed


def _default_stage_sources() -> dict[str, dict[str, Any] | None]:
    return {
        "fingerprint": _fingerprint_payload(),
        "metadata": _metadata_payload(),
        "detect": _detection_unavailable_payload(),
        "forensics": _forensics_payload(),
        "xai": _xai_unavailable_payload(),
    }


def test_stage_completes_with_full_default_pipeline(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _default_stage_sources()))
    assert payload["status"] == "COMPLETED"
    assert payload["availability"] == {
        "FINGERPRINT": "AVAILABLE",
        "METADATA": "AVAILABLE",
        "DETECTION": "UNAVAILABLE",
        "VISUAL_FORENSICS": "AVAILABLE",
        "XAI": "UNAVAILABLE",
    }
    assert payload["confidence"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["confidence"]["value"] is None
    codes = {item["code"] for item in payload["evidence"]}
    assert "detection.prediction" not in codes
    assert "xai.explanation" not in codes


def test_stage_consumes_persisted_results_without_image_file(tmp_path: Path) -> None:
    payload = asyncio.run(
        _run_stage(
            tmp_path,
            _default_stage_sources(),
            storage_path="ghost-file-that-does-not-exist.png",
        )
    )
    assert payload["status"] == "COMPLETED"
    assert payload["summary"]["total"] >= 1


def test_stage_missing_source_stages_recorded_unavailable(tmp_path: Path) -> None:
    payload = asyncio.run(
        _run_stage(
            tmp_path,
            _default_stage_sources(),
            missing={"detect", "xai"},
        )
    )
    assert payload["status"] == "COMPLETED"
    assert payload["availability"]["DETECTION"] == "UNAVAILABLE"
    assert payload["availability"]["XAI"] == "UNAVAILABLE"
    assert any("DETECTION evidence is unavailable" in note for note in payload["limitations"])


def test_stage_source_failure_does_not_fail_evidence(tmp_path: Path) -> None:
    payload = asyncio.run(
        _run_stage(
            tmp_path,
            _default_stage_sources(),
            failed={"forensics"},
        )
    )
    assert payload["status"] == "COMPLETED"
    assert payload["availability"]["VISUAL_FORENSICS"] == "FAILED"
    assert any(
        "VISUAL_FORENSICS evidence is failed" in note for note in payload["limitations"]
    )
    assert all(
        item["source"] != "VISUAL_FORENSICS" for item in payload["evidence"]
    )


def test_stage_unparseable_payload_is_unavailable(tmp_path: Path) -> None:
    scan = _scan_with_sources(_default_stage_sources())
    detect = next(s for s in scan.stages if s.name == "detect")
    detect.result_ref = "{not valid json"
    media = Media(
        original_filename="x.png",
        media_type=MediaType.IMAGE,
        storage_path="x.png",
        mime_type="image/png",
    )
    stage = EvidenceAggregationStage()
    result = asyncio.run(stage.run(_ctx(tmp_path, media, scan=scan)))
    assert result is not None and result.result_ref is not None
    payload = json.loads(result.result_ref)
    assert payload["availability"]["DETECTION"] == "UNAVAILABLE"
    assert any("could not be parsed" in note for note in payload["limitations"])


def test_stage_real_prediction_still_no_fabricated_confidence(tmp_path: Path) -> None:
    sources = _default_stage_sources()
    sources["detect"] = _stub_detection_payload()
    sources["xai"] = _xai_completed_payload()
    payload = asyncio.run(_run_stage(tmp_path, sources))
    assert payload["availability"]["DETECTION"] == "AVAILABLE"
    codes = {item["code"] for item in payload["evidence"]}
    assert "detection.prediction" in codes
    assert payload["confidence"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["confidence"]["value"] is None
    assert "not the probability" in payload["confidence"]["semantics"]


def test_stage_result_ref_deterministic(tmp_path: Path) -> None:
    name = "deterministic.png"
    media = Media(
        original_filename=name,
        media_type=MediaType.IMAGE,
        storage_path=name,
        mime_type="image/png",
    )
    scan = _scan_with_sources(_default_stage_sources())
    stage = EvidenceAggregationStage()
    ctx = _ctx(tmp_path, media, scan=scan)
    first = asyncio.run(stage.run(ctx))
    second = asyncio.run(stage.run(ctx))
    assert first is not None and second is not None
    assert first.result_ref == second.result_ref


def test_stage_rejects_video_media(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(
            _run_stage(
                tmp_path,
                _default_stage_sources(),
                media_type=MediaType.VIDEO,
            )
        )


def test_stage_registered_after_xai() -> None:
    from app.workers.stages import build_default_registry

    registry = build_default_registry()
    implemented = registry.names()
    assert "evidence" in implemented
    assert implemented.index("xai") < implemented.index("evidence")


# --------------------------------------------------------------------------- #
# Worker end-to-end
# --------------------------------------------------------------------------- #

def _worker(tmp_path: Path) -> AnalysisWorker:
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(DetectionStage())
    registry.register(VisualForensicsStage())
    registry.register(XAIStage())
    registry.register(EvidenceAggregationStage())
    execution = ScanExecutionService(
        registry=registry,
        settings=Settings(media_storage_root=tmp_path),
    )
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=0.01,
    )


async def _queued_scan(
    db_session: AsyncSession, tmp_path: Path, *, filename: str, content: bytes
) -> Scan:
    (tmp_path / filename).write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename=filename,
            media_type=MediaType.IMAGE,
            storage_path=filename,
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


async def _reload(db_session: AsyncSession, scan_id: uuid.UUID) -> Scan:
    loaded = await ScanRepository(db_session).get(scan_id)
    assert loaded is not None
    return loaded


async def test_worker_evidence_completed_with_honest_unavailable(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(
        db_session, tmp_path, filename="e.png", content=_png_bytes()
    )
    worker = _worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["evidence"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["evidence"].result_ref or "{}")
    assert payload["availability"] == {
        "FINGERPRINT": "AVAILABLE",
        "METADATA": "AVAILABLE",
        "DETECTION": "UNAVAILABLE",
        "VISUAL_FORENSICS": "AVAILABLE",
        "XAI": "UNAVAILABLE",
    }
    assert payload["confidence"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["confidence"]["value"] is None
    assert any("DETECTION evidence is unavailable" in r for r in payload["confidence"]["reasons"])


async def test_worker_evidence_confidence_not_fabricated_with_real_detector(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    from app.inference.registry import DetectorRegistry

    class StubDetector:
        name = "stub-image"
        media_type = MediaType.IMAGE

        @property
        def identity(self) -> DetectorIdentity:
            return DetectorIdentity(
                name=self.name,
                model_name="stub-model",
                model_version="0.0.1",
                checkpoint_sha256="b" * 64,
                preprocessing_version="pre-1",
            )

        def detect(self, path: Path, *, device: str) -> DetectionResult:
            return DetectionResult(
                detector=self.identity,
                media_type=self.media_type,
                prediction=DetectionPrediction(
                    label="FAKE",
                    score=0.9,
                    score_semantics="sigmoid probability",
                    class_list=("REAL", "FAKE"),
                ),
                inference=InferenceSummary(status="AVAILABLE", device=device),
                evidence_type=EvidenceType.INFERENCE,
            )

    detectors = DetectorRegistry()
    detectors.register(StubDetector())
    queued = await _queued_scan(
        db_session, tmp_path, filename="f.png", content=_png_bytes()
    )
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(DetectionStage(detectors=detectors))
    registry.register(VisualForensicsStage())
    registry.register(XAIStage(detectors=detectors))
    registry.register(EvidenceAggregationStage())
    execution = ScanExecutionService(
        registry=registry,
        settings=Settings(media_storage_root=tmp_path),
    )
    worker = AnalysisWorker(
        session_factory=SessionFactory, execution=execution, poll_interval=0.01
    )

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    payload = json.loads(by_name["evidence"].result_ref or "{}")
    assert payload["availability"]["DETECTION"] == "AVAILABLE"
    codes = {item["code"] for item in payload["evidence"]}
    assert "detection.prediction" in codes
    assert payload["confidence"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["confidence"]["value"] is None
