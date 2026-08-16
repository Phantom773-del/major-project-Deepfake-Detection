"""Decision-layer tests: confidence, risk and verdict engines and stages.

Scientific-honesty focus: the decision layer must never fabricate a numeric
confidence, an elevated risk, or a definitive verdict. The engines consume the
normalized ``EvidenceResult`` from the evidence stage and never re-run analysis.

Fixtures marked *stub* are explicitly labeled test doubles — they exercise
future paths but must never produce real conclusions.
"""

import asyncio
import json
import uuid
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from app.assessment import (
    AssessmentDimension,
    ConfidenceEngine,
    RiskEngine,
    RiskLevel,
    VerdictEngine,
    VerdictStatus,
)
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan, ScanStage
from app.db.session import SessionFactory
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import EvidenceType, MediaType, ScanStatus, StageStatus
from app.evidence import EvidenceAvailability, SourceOutput, aggregate_evidence
from app.evidence.domain import (
    ConfidenceAssessment,
    ConfidenceStatus,
    EvidenceCategory,
    EvidenceDirection,
    EvidenceItem,
    EvidenceMethodology,
    EvidenceResult,
    EvidenceSource,
    EvidenceSummary,
)
from app.inference.detectors.unavailable import UnavailableDetector
from app.media.hashing import sha256_of_bytes
from app.media.storage import LocalStorageProvider
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.execution import ScanExecutionService
from app.services.scans import ScanService
from app.workers.queue import AnalysisWorker, build_default_worker
from app.workers.registry import StageRegistry
from app.workers.stages import build_default_registry
from app.workers.stages.base import StageContext, StageError
from app.workers.stages.confidence import ConfidenceStage
from app.workers.stages.detect import DetectionStage
from app.workers.stages.evidence import EvidenceAggregationStage
from app.workers.stages.fingerprint import FingerprintStage
from app.workers.stages.forensics import VisualForensicsStage
from app.workers.stages.metadata import MetadataStage
from app.workers.stages.risk import RiskStage
from app.workers.stages.validate import ValidateStage
from app.workers.stages.verdict import VerdictStage
from app.workers.stages.xai import XAIStage
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
        "software": [],
        "consistency": {"findings": [], "count": 0},
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


def _aggregate(sources: dict[str, dict[str, object]]) -> EvidenceResult:
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
        settings=Settings(media_storage_root=tmp_path, detection_device="cpu"),
    )


# --------------------------------------------------------------------------- #
# Evidence fixtures
# --------------------------------------------------------------------------- #


def _default_evidence() -> EvidenceResult:
    """The evidence a real default scan produces (all neutral, detection/xai
    unavailable)."""
    return _aggregate(_default_sources())


def _stub_evidence(
    *,
    detection_direction: EvidenceDirection = EvidenceDirection.SUPPORTING_SYNTHETIC,
) -> EvidenceResult:
    """STUB evidence — a test double labeled as such, never real output. Carries
    a detector inference with a high score plus a correlated XAI item."""
    return EvidenceResult(
        methodology=EvidenceMethodology(),
        availability={
            EvidenceSource.FINGERPRINT: EvidenceAvailability.AVAILABLE,
            EvidenceSource.METADATA: EvidenceAvailability.AVAILABLE,
            EvidenceSource.DETECTION: EvidenceAvailability.AVAILABLE,
            EvidenceSource.VISUAL_FORENSICS: EvidenceAvailability.AVAILABLE,
            EvidenceSource.XAI: EvidenceAvailability.AVAILABLE,
        },
        evidence=[
            EvidenceItem(
                code="detection.prediction",
                source=EvidenceSource.DETECTION,
                category=EvidenceCategory.SYNTHETIC_GENERATION,
                evidence_type=EvidenceType.INFERENCE,
                observation="stub detector output",
                interpretation="stub: supports synthetic generation",
                direction=detection_direction,
                correlation_group="model-inference",
                details={"score": 0.93, "score_semantics": "sigmoid probability"},
            ),
            EvidenceItem(
                code="xai.explanation",
                source=EvidenceSource.XAI,
                category=EvidenceCategory.MODEL_BEHAVIOR,
                evidence_type=EvidenceType.INFERENCE,
                observation="stub explanation",
                interpretation="stub: correlated with detector inference",
                direction=EvidenceDirection.NEUTRAL,
                correlation_group="model-inference",
            ),
        ],
        summary=EvidenceSummary(
            total=2,
            independent_count=1,
            by_evidence_type={"INFERENCE": 2},
            by_direction={detection_direction.value: 1, "NEUTRAL": 1},
        ),
        confidence=ConfidenceAssessment(
            status=ConfidenceStatus.INSUFFICIENT_EVIDENCE,
            value=None,
            semantics="stub",
        ),
    )


def _stub_editing_history_evidence() -> EvidenceResult:
    """STUB evidence whose only directional item leans toward editing history
    (a manipulation signal), never synthetic generation."""
    return _stub_evidence(
        detection_direction=EvidenceDirection.SUPPORTING_EDITING_HISTORY
    )


# --------------------------------------------------------------------------- #
# Confidence engine (10 scenarios)
# --------------------------------------------------------------------------- #


def test_confidence_default_evidence_is_insufficient_and_deterministic() -> None:
    first = ConfidenceEngine.assess(_default_evidence())
    second = ConfidenceEngine.assess(_default_evidence())
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert first.value is None


def test_confidence_missing_evidence_fails_safe() -> None:
    result = ConfidenceEngine.assess(None)
    assert result.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert result.value is None
    assert any(
        "no evidence was available" in limitation for limitation in result.limitations
    )


def test_confidence_empty_evidence_is_insufficient() -> None:
    evidence = _default_evidence()
    evidence.evidence = []
    result = ConfidenceEngine.assess(evidence)
    assert result.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert any("no evidence items were produced" in r for r in result.reasons)


def test_confidence_never_emits_numeric_value() -> None:
    for evidence in (_default_evidence(), _stub_evidence()):
        result = ConfidenceEngine.assess(evidence)
        assert result.value is None
        assert result.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE


def test_confidence_methodology_version_present() -> None:
    assert ConfidenceEngine.assess(_default_evidence()).methodology_version == "1"
    assert ConfidenceEngine.assess(None).methodology_version == "1"


def test_confidence_semantics_never_probability() -> None:
    semantics = ConfidenceEngine.assess(_default_evidence()).semantics
    assert "never the probability that the media is fake" in semantics


def test_confidence_unavailable_detector_is_not_negative_evidence() -> None:
    result = ConfidenceEngine.assess(_default_evidence())
    assert result.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert any(
        "DETECTION evidence is unavailable" in limitation
        for limitation in result.limitations
    )
    assert any(
        "not negative evidence" in limitation for limitation in result.limitations
    )


def test_confidence_stub_directional_evidence_still_insufficient() -> None:
    result = ConfidenceEngine.assess(_stub_evidence())
    assert result.confidence_status is ConfidenceStatus.INSUFFICIENT_EVIDENCE
    assert result.value is None
    assert any("no validated methodology" in r for r in result.reasons)


def test_confidence_stub_detector_score_is_not_probability() -> None:
    result = ConfidenceEngine.assess(_stub_evidence())
    assert result.value is None
    assert any(
        "not a calibrated probability" in limitation
        for limitation in result.limitations
    )


def test_confidence_basis_classifies_directionally() -> None:
    result = ConfidenceEngine.assess(_stub_evidence())
    detection = next(r for r in result.basis if r.code == "detection.prediction")
    xai = next(r for r in result.basis if r.code == "xai.explanation")
    assert detection.directional is True
    assert detection.dimension is AssessmentDimension.SYNTHETIC
    assert xai.directional is False
    assert xai.dimension is AssessmentDimension.UNKNOWN
    assert result.by_dimension[AssessmentDimension.SYNTHETIC] == 1
    assert result.by_dimension[AssessmentDimension.UNKNOWN] == 1


def test_confidence_default_basis_all_neutral() -> None:
    result = ConfidenceEngine.assess(_default_evidence())
    assert result.basis
    assert all(not r.directional for r in result.basis)
    assert all(r.dimension is AssessmentDimension.UNKNOWN for r in result.basis)
    assert result.by_dimension[AssessmentDimension.UNKNOWN] == len(result.basis)


# --------------------------------------------------------------------------- #
# Risk engine (7 scenarios)
# --------------------------------------------------------------------------- #


def test_risk_default_evidence_is_undetermined() -> None:
    evidence = _default_evidence()
    confidence = ConfidenceEngine.assess(evidence)
    result = RiskEngine.assess(evidence, confidence)
    assert result.risk_level is RiskLevel.UNDETERMINED
    assert result.value is None


def test_risk_missing_confidence_fails_safe() -> None:
    result = RiskEngine.assess(None, None)
    assert result.risk_level is RiskLevel.UNDETERMINED
    assert any("SUFFICIENT_EVIDENCE" in r for r in result.reasons)


def test_risk_high_stub_score_does_not_elevate() -> None:
    evidence = _stub_evidence()
    confidence = ConfidenceEngine.assess(evidence)
    result = RiskEngine.assess(evidence, confidence)
    assert result.risk_level is RiskLevel.UNDETERMINED
    assert any(
        "raw detector score never determines risk" in limitation
        for limitation in result.limitations
    )


def test_risk_is_independent_from_confidence_value() -> None:
    evidence = _default_evidence()
    confidence = ConfidenceEngine.assess(evidence)
    assert confidence.value is None
    assert RiskEngine.assess(evidence, confidence).risk_level is RiskLevel.UNDETERMINED
    assert RiskEngine.assess(evidence, None).risk_level is RiskLevel.UNDETERMINED


def test_risk_methodology_version_present() -> None:
    assert (
        RiskEngine.assess(_default_evidence(), ConfidenceEngine.assess(None))
    ).methodology_version == "1"


def test_risk_basis_only_directional_references() -> None:
    evidence = _stub_evidence()
    result = RiskEngine.assess(evidence, ConfidenceEngine.assess(evidence))
    assert result.basis
    assert all(r.directional for r in result.basis)
    assert all(r.code == "detection.prediction" for r in result.basis)


def test_risk_is_deterministic() -> None:
    evidence = _default_evidence()
    confidence = ConfidenceEngine.assess(evidence)
    assert RiskEngine.assess(evidence, confidence).model_dump(mode="json") == (
        RiskEngine.assess(evidence, confidence).model_dump(mode="json")
    )


# --------------------------------------------------------------------------- #
# Verdict engine (7 scenarios)
# --------------------------------------------------------------------------- #


def test_verdict_default_evidence_is_insufficient() -> None:
    evidence = _default_evidence()
    result = VerdictEngine.reach(evidence, ConfidenceEngine.assess(evidence))
    assert result.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE


def test_verdict_missing_confidence_fails_safe() -> None:
    result = VerdictEngine.reach(None, None)
    assert result.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE


def test_verdict_stub_high_score_is_not_a_conclusion() -> None:
    evidence = _stub_evidence()
    result = VerdictEngine.reach(evidence, ConfidenceEngine.assess(evidence))
    assert result.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE
    assert any(
        "detector score alone never produces a verdict" in limitation
        for limitation in result.limitations
    )


def test_verdict_never_claims_authentic_or_synthetic() -> None:
    for evidence in (
        _default_evidence(),
        _stub_evidence(),
        _stub_editing_history_evidence(),
    ):
        result = VerdictEngine.reach(evidence, ConfidenceEngine.assess(evidence))
        assert result.verdict not in {
            VerdictStatus.LIKELY_AUTHENTIC,
            VerdictStatus.LIKELY_MANIPULATED,
            VerdictStatus.LIKELY_SYNTHETIC,
        }


def test_verdict_manipulation_stays_distinct_from_synthetic() -> None:
    evidence = _stub_editing_history_evidence()
    result = VerdictEngine.reach(evidence, ConfidenceEngine.assess(evidence))
    assert result.verdict is VerdictStatus.INSUFFICIENT_EVIDENCE
    editing = next(r for r in result.basis if r.code == "detection.prediction")
    assert editing.dimension is AssessmentDimension.MANIPULATED
    assert editing.directional is True


def test_verdict_methodology_version_present() -> None:
    assert (
        VerdictEngine.reach(_default_evidence(), ConfidenceEngine.assess(None))
    ).methodology_version == "1"


def test_verdict_basis_includes_all_evidence() -> None:
    evidence = _default_evidence()
    result = VerdictEngine.reach(evidence, ConfidenceEngine.assess(evidence))
    assert len(result.basis) == len(evidence.evidence)


# --------------------------------------------------------------------------- #
# Pipeline integration (6 scenarios)
# --------------------------------------------------------------------------- #


def test_pipeline_registers_decision_stages_after_evidence() -> None:
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
    ]
    implemented = registry.names()
    assert [name for name in STAGE_ORDER if name in registry] == implemented
    assert implemented.index("evidence") < implemented.index("confidence")
    assert implemented.index("confidence") < implemented.index("risk")
    assert implemented.index("risk") < implemented.index("verdict")


async def test_worker_decision_stages_completed_with_honest_results(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path)
    worker = _worker(tmp_path)
    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    for name in ("confidence", "risk", "verdict"):
        assert by_name[name].status is StageStatus.COMPLETED
        assert by_name[name].result_ref is not None
    assert by_name["report"].status is StageStatus.SKIPPED
    confidence_payload = json.loads(by_name["confidence"].result_ref or "{}")
    assert confidence_payload["confidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert confidence_payload["value"] is None
    assert confidence_payload["methodology_version"] == "1"
    assert confidence_payload["basis"]
    risk_payload = json.loads(by_name["risk"].result_ref or "{}")
    assert risk_payload["risk_level"] == "UNDETERMINED"
    verdict_payload = json.loads(by_name["verdict"].result_ref or "{}")
    assert verdict_payload["verdict"] == "INSUFFICIENT_EVIDENCE"


async def test_api_scan_decision_stages_completed(
    client: Any, db_session: AsyncSession
) -> None:
    upload = await client.post(
        "/api/v1/media/upload",
        files={"file": ("decision.png", _png_bytes(), "image/png")},
    )
    assert upload.status_code == 201
    media_id = upload.json()["data"]["id"]
    created = await client.post("/api/v1/scans", json={"media_id": media_id})
    assert created.status_code == 201
    scan_id = created.json()["data"]["id"]
    scan = await ScanService(db_session).get_scan(scan_id=scan_id)
    await ScanService(db_session).transition(scan, to=ScanStatus.VALIDATING)
    await ScanService(db_session).transition(scan, to=ScanStatus.QUEUED)
    await db_session.commit()

    worker = build_default_worker()
    assert await worker.run_until_idle() == 1

    detail = await client.get(f"/api/v1/scans/{scan_id}")
    assert detail.status_code == 200
    stages = {s["name"]: s for s in detail.json()["data"]["stages"]}
    assert stages["confidence"]["status"] == "COMPLETED"
    assert stages["risk"]["status"] == "COMPLETED"
    assert stages["verdict"]["status"] == "COMPLETED"
    assert stages["report"]["status"] == "SKIPPED"


def test_decision_stages_reject_video_media(tmp_path: Path) -> None:
    media = Media(
        original_filename="v.png",
        media_type=MediaType.VIDEO,
        storage_path="v.png",
        mime_type="image/png",
    )
    scan = _scan_with_sources({})
    for stage in (ConfidenceStage(), RiskStage(), VerdictStage()):
        with pytest.raises(StageError, match="not supported"):
            asyncio.run(stage.run(_ctx(tmp_path, media, scan=scan)))


def test_confidence_stage_reads_evidence_result(tmp_path: Path) -> None:
    sources = dict(_default_sources())
    sources["evidence"] = _aggregate(sources).model_dump(mode="json")
    media = Media(
        original_filename="c.png",
        media_type=MediaType.IMAGE,
        storage_path="c.png",
        mime_type="image/png",
    )
    scan = _scan_with_sources(sources)
    result = asyncio.run(ConfidenceStage().run(_ctx(tmp_path, media, scan=scan)))
    assert result is not None and result.result_ref is not None
    payload = json.loads(result.result_ref)
    assert payload["confidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["value"] is None
    assert len(payload["basis"]) == len(_default_evidence().evidence)


def test_confidence_stage_fails_safe_without_evidence_result(
    tmp_path: Path,
) -> None:
    media = Media(
        original_filename="d.png",
        media_type=MediaType.IMAGE,
        storage_path="d.png",
        mime_type="image/png",
    )
    scan = _scan_with_sources({}, missing={"evidence"})
    result = asyncio.run(ConfidenceStage().run(_ctx(tmp_path, media, scan=scan)))
    assert result is not None and result.result_ref is not None
    payload = json.loads(result.result_ref)
    assert payload["confidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["value"] is None
    assert any("no evidence was available" in r for r in payload["limitations"])


# --------------------------------------------------------------------------- #
# Helpers (mirroring test_evidence / test_worker)
# --------------------------------------------------------------------------- #


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


async def _reload(db_session: AsyncSession, scan_id: uuid.UUID) -> Scan:
    loaded = await ScanRepository(db_session).get(scan_id)
    assert loaded is not None
    return loaded


def _worker(tmp_path: Path) -> AnalysisWorker:
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(DetectionStage())
    registry.register(VisualForensicsStage())
    registry.register(XAIStage())
    registry.register(EvidenceAggregationStage())
    registry.register(ConfidenceStage())
    registry.register(RiskStage())
    registry.register(VerdictStage())
    execution = ScanExecutionService(
        registry=registry,
        settings=Settings(media_storage_root=tmp_path),
    )
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=0.01,
    )
