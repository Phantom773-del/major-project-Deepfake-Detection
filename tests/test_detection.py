"""Detection intelligence tests (contract, registry, stage, pipeline).

Uses controlled stub detectors for inference; the honest UnavailableDetector
covers the no-model state. Real model integration would be a separate,
explicitly-marked test.
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
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import EvidenceType, MediaType, ScanStatus, StageStatus
from app.inference.base import (
    DetectionPrediction,
    DetectionResult,
    DetectorError,
    DetectorIdentity,
    InferenceSummary,
)
from app.inference.detectors import build_default_detector_registry
from app.inference.detectors.unavailable import UnavailableDetector
from app.inference.registry import DetectorRegistry
from app.media.hashing import sha256_of_bytes
from app.media.storage import LocalStorageProvider
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.execution import ScanExecutionService
from app.services.scans import ScanService
from app.workers.queue import AnalysisWorker
from app.workers.registry import StageRegistry
from app.workers.stages import build_default_registry
from app.workers.stages.base import StageContext, StageError
from app.workers.stages.detect import DetectionStage
from app.workers.stages.fingerprint import FingerprintStage
from app.workers.stages.metadata import MetadataStage
from app.workers.stages.validate import ValidateStage
from PIL import Image
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession


class StubDetector:
    """Controlled test detector implementing the Detector contract."""

    name = "stub-image"
    media_type = MediaType.IMAGE

    def __init__(
        self,
        *,
        model_name: str = "stub-model",
        model_version: str = "0.0.1",
        score: float = 0.87,
        fail: bool = False,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._score = score
        self._fail = fail
        self.calls: list[str] = []

    @property
    def identity(self) -> DetectorIdentity:
        return DetectorIdentity(
            name=self.name,
            model_name=self._model_name,
            model_version=self._model_version,
            checkpoint_sha256="a" * 64,
            preprocessing_version="pre-1",
        )

    def detect(self, path: Path, *, device: str) -> DetectionResult:
        self.calls.append(str(path))
        if self._fail:
            raise DetectorError("simulated inference failure")
        return DetectionResult(
            detector=self.identity,
            media_type=self.media_type,
            prediction=DetectionPrediction(
                label="FAKE",
                score=self._score,
                score_semantics="sigmoid probability",
                class_list=("REAL", "FAKE"),
            ),
            inference=InferenceSummary(status="AVAILABLE", device=device),
            evidence_type=EvidenceType.INFERENCE,
        )


def _png_bytes(width: int = 12, height: int = 9) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (120, 40, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _media(*, storage_path: str, mime_type: str = "image/png") -> Media:
    return Media(
        original_filename=storage_path,
        media_type=MediaType.IMAGE,
        storage_path=storage_path,
        mime_type=mime_type,
    )


def _scan() -> Scan:
    return Scan(media_id=uuid.uuid4())


def _ctx(
    tmp_path: Path, media: Media, *, device: str = "cpu"
) -> StageContext:
    return StageContext(
        scan=_scan(),
        media=media,
        storage=LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path, detection_device=device),
    )


def _write(tmp_path: Path, content: bytes = _png_bytes()) -> tuple[Path, str]:
    name = f"det-{uuid.uuid4().hex}.png"
    path = tmp_path / name
    path.write_bytes(content)
    return path, name


async def _run_stage(
    tmp_path: Path,
    content: bytes = _png_bytes(),
    *,
    detectors: DetectorRegistry | None = None,
    mime_type: str = "image/png",
    media_type: MediaType = MediaType.IMAGE,
    device: str = "cpu",
) -> Any:
    path, name = _write(tmp_path, content)
    media = Media(
        original_filename=name,
        media_type=media_type,
        storage_path=name,
        mime_type=mime_type,
    )
    result = await DetectionStage(detectors=detectors).run(_ctx(tmp_path, media, device=device))
    assert result is not None and result.result_ref is not None
    return json.loads(result.result_ref)


def _stub_registry(*args: object, **kwargs: object) -> DetectorRegistry:
    registry = DetectorRegistry()
    registry.register(StubDetector(**kwargs))  # type: ignore[arg-type]
    return registry


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


def _worker(
    tmp_path: Path,
    *,
    detect: DetectionStage | None = None,
) -> AnalysisWorker:
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(detect or DetectionStage())
    execution = ScanExecutionService(
        registry=registry,
        settings=Settings(media_storage_root=tmp_path),
    )
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=0.01,
    )


# --------------------------------------------------------------------------- #
# Detector contract
# --------------------------------------------------------------------------- #

def test_detector_contract_shape(tmp_path: Path) -> None:
    detector = StubDetector()
    assert detector.name == "stub-image"
    assert detector.media_type is MediaType.IMAGE
    identity = detector.identity
    assert identity.name == "stub-image"
    assert identity.detector_version == "1"
    result = detector.detect(tmp_path / "nonexistent.png", device="cpu")
    assert isinstance(result, DetectionResult)
    assert result.evidence_type is EvidenceType.INFERENCE


def test_detection_result_validation() -> None:
    base = dict(
        detector=DetectorIdentity(name="x"),
        media_type=MediaType.IMAGE,
        inference=InferenceSummary(status="AVAILABLE"),
    )
    with pytest.raises(ValidationError):
        DetectionPrediction(label="", score=0.5, score_semantics="sigmoid")
    with pytest.raises(ValidationError):
        DetectionPrediction(label="FAKE", score=1.5, score_semantics="sigmoid")
    with pytest.raises(ValidationError):
        DetectionPrediction(label="FAKE", score=-0.1, score_semantics="sigmoid")
    with pytest.raises(ValidationError):
        DetectionPrediction(label="FAKE", score=0.5, score_semantics="")
    valid = DetectionPrediction(label="FAKE", score=0.5, score_semantics="sigmoid probability")
    result = DetectionResult(**base, prediction=valid, evidence_type=EvidenceType.INFERENCE)
    assert result.prediction is not None and result.prediction.label == "FAKE"


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_registry_register_and_lookup() -> None:
    registry = DetectorRegistry()
    detector = StubDetector()
    registry.register(detector)
    assert registry.get("stub-image") is detector
    assert "stub-image" in registry
    assert registry.names() == ["stub-image"]
    assert len(registry) == 1


def test_registry_rejects_duplicate_detector() -> None:
    registry = DetectorRegistry()
    registry.register(StubDetector())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(StubDetector())


def test_registry_find_by_media_type() -> None:
    registry = _stub_registry()
    assert registry.find(MediaType.IMAGE) is not None
    assert registry.find(MediaType.IMAGE).name == "stub-image"  # type: ignore[union-attr]


def test_registry_unsupported_media_type_returns_none() -> None:
    registry = _stub_registry()
    assert registry.find(MediaType.VIDEO) is None


# --------------------------------------------------------------------------- #
# Unavailable model behavior
# --------------------------------------------------------------------------- #

def test_default_registry_has_unavailable_detector() -> None:
    registry = build_default_detector_registry()
    detector = registry.find(MediaType.IMAGE)
    assert detector is not None
    assert detector.name == "unavailable"
    assert isinstance(detector, UnavailableDetector)


def test_unavailable_detector_never_fabricates_prediction(tmp_path: Path) -> None:
    detector = UnavailableDetector()
    result = detector.detect(tmp_path / "any.png", device="cpu")
    assert result.inference.status == "UNAVAILABLE"
    assert result.prediction is None
    assert result.evidence_type is None
    assert result.detector.model_name is None
    assert result.detector.model_version is None
    assert result.detector.checkpoint_sha256 is None
    assert "no image detector" in (result.inference.reason or "")


# --------------------------------------------------------------------------- #
# Detection stage
# --------------------------------------------------------------------------- #

def test_stage_registered_after_metadata() -> None:
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
    assert implemented.index("metadata") < implemented.index("detect")


def test_stage_with_default_detectors_is_unavailable(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path))
    assert payload["inference"]["status"] == "UNAVAILABLE"
    assert payload["prediction"] is None
    assert payload["evidence_type"] is None
    assert payload["detector"]["name"] == "unavailable"


def test_stage_runs_stub_detector(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, detectors=_stub_registry(score=0.9)))
    assert payload["inference"]["status"] == "AVAILABLE"
    assert payload["prediction"] == {
        "label": "FAKE",
        "score": 0.9,
        "score_semantics": "sigmoid probability",
        "class_list": ["REAL", "FAKE"],
    }
    assert payload["evidence_type"] == "INFERENCE"


def test_stage_inference_failure_is_client_safe(tmp_path: Path) -> None:
    registry = DetectorRegistry()
    registry.register(StubDetector(fail=True))
    with pytest.raises(StageError, match="simulated inference failure"):
        asyncio.run(_run_stage(tmp_path, detectors=registry))


def test_stage_rejects_video_media(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(
            _run_stage(
                tmp_path,
                mime_type="video/mp4",
                media_type=MediaType.VIDEO,
            )
        )


def test_stage_missing_file(tmp_path: Path) -> None:
    stage, ctx = DetectionStage(), _ctx(tmp_path, _media(storage_path="ghost.png"))
    with pytest.raises(StageError, match="stored media file is missing"):
        asyncio.run(stage.run(ctx))


def test_cpu_fallback_device_passed_to_detector(tmp_path: Path) -> None:
    detector = StubDetector()
    registry = DetectorRegistry()
    registry.register(detector)
    path, name = _write(tmp_path)
    media = _media(storage_path=name)
    result = asyncio.run(
        DetectionStage(detectors=registry).run(_ctx(tmp_path, media, device="cpu"))
    )
    assert result is not None
    payload = json.loads(result.result_ref or "{}")
    assert payload["inference"]["device"] == "cpu"
    assert detector.calls and detector.calls[0] == str(path)


def test_result_ref_structure(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, detectors=_stub_registry()))
    assert set(payload) == {"detector", "media_type", "prediction", "inference", "evidence_type"}
    assert set(payload["detector"]) == {
        "name", "detector_version", "model_name", "model_version",
        "checkpoint_sha256", "preprocessing_version",
    }
    assert set(payload["inference"]) == {"status", "reason", "device", "duration_ms"}
    assert payload["media_type"] == "IMAGE"


def test_result_ref_deterministic(tmp_path: Path) -> None:
    stage = DetectionStage(detectors=_stub_registry())
    path, name = _write(tmp_path)
    ctx = _ctx(tmp_path, _media(storage_path=name))
    first = asyncio.run(stage.run(ctx))
    second = asyncio.run(stage.run(ctx))
    assert first is not None and second is not None
    assert first.result_ref == second.result_ref


# --------------------------------------------------------------------------- #
# Pipeline integration
# --------------------------------------------------------------------------- #

async def test_worker_detect_stage_completed_unavailable(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path, filename="d.png", content=_png_bytes())
    worker = _worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["detect"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["detect"].result_ref or "{}")
    assert payload["inference"]["status"] == "UNAVAILABLE"
    assert payload["prediction"] is None


async def test_worker_detect_stage_with_stub_detector(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    detector = StubDetector()
    registry = DetectorRegistry()
    registry.register(detector)
    queued = await _queued_scan(db_session, tmp_path, filename="d.png", content=_png_bytes())
    worker = _worker(tmp_path, detect=DetectionStage(detectors=registry))

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    by_name = {s.name: s for s in scan.stages}
    assert by_name["detect"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["detect"].result_ref or "{}")
    assert payload["inference"]["status"] == "AVAILABLE"
    assert payload["prediction"]["label"] == "FAKE"
    assert payload["evidence_type"] == "INFERENCE"
    assert detector.calls


async def test_worker_fails_scan_on_detection_error(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    registry = DetectorRegistry()
    registry.register(StubDetector(fail=True))
    queued = await _queued_scan(db_session, tmp_path, filename="d.png", content=_png_bytes())
    worker = _worker(tmp_path, detect=DetectionStage(detectors=registry))

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.FAILED
    assert "simulated inference failure" in (scan.error_message or "")
