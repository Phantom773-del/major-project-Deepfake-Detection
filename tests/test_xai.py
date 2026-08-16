"""XAI engine tests (contract, registry, explainer, stage, pipeline).

Uses controlled stub detectors for detection results and stub explainers for
the compatible-explainer path. The honest UnavailableExplainer covers the
no-model state. No fake heatmap is ever produced or asserted as real: the only
heatmap-bearing payloads come from an explicitly-registered stub explainer in
unit tests.
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
from app.domain.taxonomy import EvidenceType, MediaType, ScanStatus, StageStatus
from app.inference.base import (
    DetectionPrediction,
    DetectionResult,
    DetectorIdentity,
    InferenceSummary,
)
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
from app.workers.stages.xai import XAIStage
from app.xai.base import (
    XAIError,
    XAIExplanationContext,
    XAIHeatmap,
    XAIInterpretation,
    XAIResult,
)
from app.xai.explainers import build_default_xai_explainer_registry
from app.xai.explainers.unavailable import UnavailableExplainer
from app.xai.registry import XAIExplainerRegistry
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
        unavailable: bool = False,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._score = score
        self._unavailable = unavailable
        self.calls: list[str] = []

    @property
    def identity(self) -> DetectorIdentity:
        return DetectorIdentity(
            name=self.name,
            model_name=self._model_name,
            model_version=self._model_version,
            checkpoint_sha256="b" * 64,
            preprocessing_version="pre-1",
        )

    def detect(self, path: Path, *, device: str) -> DetectionResult:
        self.calls.append(str(path))
        if self._unavailable:
            return DetectionResult(
                detector=self.identity,
                media_type=self.media_type,
                prediction=None,
                inference=InferenceSummary(
                    status="UNAVAILABLE",
                    reason="model not loaded in this test run",
                    device=device,
                ),
                evidence_type=None,
            )
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


class GradCAMLikeExplainer:
    """Stub explainer that reports a real heatmap only in this test context.

    It does NOT compute a Grad-CAM map — it exists to exercise the contract and
    stage wiring for a compatible explainer. The heatmap reference is a dummy
    string written by the test double, never produced by the pipeline.
    """

    name = "stub-gradcam"
    version = "1"
    technique = "grad-cam"
    media_type = MediaType.IMAGE
    model_type: str | None = "stub-model"

    def __init__(self) -> None:
        self.explained: list[XAIExplanationContext] = []

    def explain(
        self,
        path: Path,
        *,
        context: XAIExplanationContext,
        settings: Settings,
    ) -> XAIResult:
        self.explained.append(context)
        return XAIResult(
            status="COMPLETED",
            explainer=dict(
                name=self.name,
                version=self.version,
                technique=self.technique,
                model_type=self.model_type,
            ),
            model=dict(
                name=context.detection.detector.model_name,
                version=context.detection.detector.model_version,
                checkpoint_sha256=context.detection.detector.checkpoint_sha256,
            ),
            heatmap=XAIHeatmap(
                available=True,
                format="png",
                width=12,
                height=9,
                reference="heatmaps/stub.png",
            ),
            interpretation=XAIInterpretation(
                target_label="FAKE",
                target_score=0.87,
                score_semantics="sigmoid probability",
                summary="stub explanation",
                limitation="stub only; not a real Grad-CAM map",
            ),
        )


class FailingExplainer(GradCAMLikeExplainer):
    def explain(
        self,
        path: Path,
        *,
        context: XAIExplanationContext,
        settings: Settings,
    ) -> XAIResult:
        raise XAIError("simulated explanation failure")


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


def _scan_with_detection(payload: dict[str, Any] | None) -> Scan:
    """Build a scan whose ``detect`` stage already produced ``payload``."""
    scan = Scan(media_id=uuid.uuid4())
    stages: list[ScanStage] = []
    for sequence, name in enumerate(STAGE_ORDER):
        stage = ScanStage(name=name, status=StageStatus.PENDING, sequence=sequence)
        if name == "detect" and payload is not None:
            stage.status = StageStatus.COMPLETED
            stage.result_ref = json.dumps(payload, sort_keys=True)
        stages.append(stage)
    scan.stages = stages
    return scan


def _ctx(
    tmp_path: Path, media: Media, *, scan: Scan, device: str = "cpu"
) -> StageContext:
    return StageContext(
        scan=scan,
        media=media,
        storage=LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path, detection_device=device),
    )


def _write(tmp_path: Path, content: bytes = _png_bytes()) -> tuple[Path, str]:
    name = f"xai-{uuid.uuid4().hex}.png"
    path = tmp_path / name
    path.write_bytes(content)
    return path, name


def _detection_payload(result: DetectionResult) -> dict[str, Any]:
    return result.model_dump(mode="json")


async def _run_stage(
    tmp_path: Path,
    detection_payload: dict[str, Any] | None,
    *,
    explainers: XAIExplainerRegistry | None = None,
    detectors: DetectorRegistry | None = None,
    content: bytes = _png_bytes(),
    media_type: MediaType = MediaType.IMAGE,
) -> Any:
    path, name = _write(tmp_path, content)
    media = Media(
        original_filename=name,
        media_type=media_type,
        storage_path=name,
        mime_type="image/png",
    )
    scan = _scan_with_detection(detection_payload)
    stage = XAIStage(explainers=explainers, detectors=detectors)
    result = await stage.run(_ctx(tmp_path, media, scan=scan))
    assert result is not None and result.result_ref is not None
    return json.loads(result.result_ref)


def _default_detection_payload() -> dict[str, Any]:
    return _detection_payload(
        UnavailableDetector().detect(Path("unused"), device="cpu")
    )


def _stub_detection_payload(unavailable: bool = False) -> dict[str, Any]:
    return _detection_payload(
        StubDetector(unavailable=unavailable).detect(Path("unused"), device="cpu")
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


def _worker(
    tmp_path: Path,
    *,
    detect: DetectionStage | None = None,
    xai: XAIStage | None = None,
) -> AnalysisWorker:
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(detect or DetectionStage())
    registry.register(xai or XAIStage())
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
# XAI result contract
# --------------------------------------------------------------------------- #

def test_xai_result_validation() -> None:
    with pytest.raises(ValidationError):
        XAIResult(status="BOGUS")
    unavailable = XAIResult(status="UNAVAILABLE", reason="no model")
    assert unavailable.heatmap is None
    assert unavailable.interpretation is None
    assert unavailable.explainer is None
    completed = XAIResult(
        status="COMPLETED",
        explainer=dict(name="g", version="1", technique="grad-cam"),
        heatmap=XAIHeatmap(
            available=True, format="png", width=12, height=9, reference="h.png"
        ),
    )
    assert completed.heatmap is not None and completed.heatmap.available is True
    with pytest.raises(ValidationError):
        XAIInterpretation(target_score=1.7)  # noqa: PLC1901


def test_xai_heatmap_requires_available_when_fields_set() -> None:
    heatmap = XAIHeatmap(available=True, format="png", width=12, height=9, reference="h.png")
    assert heatmap.format == "png"
    empty = XAIHeatmap()
    assert empty.available is False
    assert empty.reference is None


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_registry_register_and_lookup() -> None:
    registry = XAIExplainerRegistry()
    explainer = UnavailableExplainer()
    registry.register(explainer)
    assert registry.get("unavailable") is explainer
    assert "unavailable" in registry
    assert registry.names() == ["unavailable"]
    assert len(registry) == 1


def test_registry_rejects_duplicate_explainer() -> None:
    registry = XAIExplainerRegistry()
    registry.register(UnavailableExplainer())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(UnavailableExplainer())


def test_registry_find_exact_model_type_wins() -> None:
    registry = XAIExplainerRegistry()
    registry.register(UnavailableExplainer())
    registry.register(GradCAMLikeExplainer())
    found = registry.find(MediaType.IMAGE, "stub-model")
    assert found is not None and found.name == "stub-gradcam"


def test_registry_find_falls_back_to_none_model_type() -> None:
    registry = XAIExplainerRegistry()
    registry.register(GradCAMLikeExplainer())
    registry.register(UnavailableExplainer())
    found = registry.find(MediaType.IMAGE, "other-model")
    assert found is not None and found.name == "unavailable"
    found_none = registry.find(MediaType.IMAGE, None)
    assert found_none is not None and found_none.name == "unavailable"


def test_registry_unsupported_media_type_returns_none() -> None:
    registry = build_default_xai_explainer_registry()
    assert registry.find(MediaType.VIDEO, None) is None


def test_default_registry_has_unavailable_explainer() -> None:
    registry = build_default_xai_explainer_registry()
    explainer = registry.find(MediaType.IMAGE, None)
    assert explainer is not None
    assert explainer.name == "unavailable"
    assert isinstance(explainer, UnavailableExplainer)


# --------------------------------------------------------------------------- #
# Unavailable explainer behavior (honest, no fabrication)
# --------------------------------------------------------------------------- #

def test_unavailable_explainer_never_fabricates_for_unavailable_detection(
    tmp_path: Path,
) -> None:
    detection = UnavailableDetector().detect(tmp_path / "any.png", device="cpu")
    context = XAIExplanationContext(
        detector=UnavailableDetector(), detection=detection, device="cpu"
    )
    result = UnavailableExplainer().explain(
        tmp_path / "any.png", context=context, settings=Settings(media_storage_root=tmp_path)
    )
    assert result.status == "UNAVAILABLE"
    assert result.heatmap is None
    assert result.interpretation is None
    assert result.model is not None
    assert result.model.name is None
    assert result.model.checkpoint_sha256 is None
    assert "no detector model produced a prediction" in (result.reason or "")


def test_unavailable_explainer_never_fabricates_for_real_prediction(
    tmp_path: Path,
) -> None:
    detection = StubDetector().detect(tmp_path / "any.png", device="cpu")
    assert detection.prediction is not None
    context = XAIExplanationContext(
        detector=StubDetector(), detection=detection, device="cpu"
    )
    result = UnavailableExplainer().explain(
        tmp_path / "any.png", context=context, settings=Settings(media_storage_root=tmp_path)
    )
    assert result.status == "UNAVAILABLE"
    assert result.heatmap is None
    assert result.interpretation is None
    assert result.model is not None and result.model.name == "stub-model"
    assert "no compatible detector model is registered for XAI" in (result.reason or "")


# --------------------------------------------------------------------------- #
# XAI stage
# --------------------------------------------------------------------------- #

def test_stage_registered_after_forensics() -> None:
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
    implemented = registry.names()
    assert [name for name in STAGE_ORDER if name in registry] == implemented
    assert implemented.index("forensics") < implemented.index("xai")
    assert implemented.index("xai") < implemented.index("evidence")
    assert implemented.index("evidence") < implemented.index("confidence")


def test_stage_default_is_unavailable_not_an_error(tmp_path: Path) -> None:
    payload = asyncio.run(
        _run_stage(tmp_path, _default_detection_payload())
    )
    assert payload["status"] == "UNAVAILABLE"
    assert "no detector model produced a prediction" in payload["reason"]
    assert payload["explainer"]["name"] == "unavailable"
    assert payload["model"] == {
        "name": None,
        "version": None,
        "checkpoint_sha256": None,
    }
    assert payload["heatmap"] is None
    assert payload["interpretation"] is None


def test_stage_unavailable_when_no_compatible_explainer(tmp_path: Path) -> None:
    detectors = DetectorRegistry()
    detectors.register(StubDetector())
    payload = asyncio.run(
        _run_stage(tmp_path, _stub_detection_payload(), detectors=detectors)
    )
    assert payload["status"] == "UNAVAILABLE"
    assert "stub-model" in payload["reason"]
    assert payload["heatmap"] is None


def test_stage_returns_unavailable_when_detect_stage_missing(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, None))
    assert payload["status"] == "UNAVAILABLE"
    assert "no detection result" in payload["reason"]


def test_stage_returns_unavailable_on_unparseable_detection(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, {"not": "a detection result"}))
    assert payload["status"] == "UNAVAILABLE"
    assert "no detection result" in payload["reason"]


def test_stage_runs_compatible_explainer_with_same_detector(tmp_path: Path) -> None:
    detector = StubDetector()
    registry = DetectorRegistry()
    registry.register(detector)
    explainer = GradCAMLikeExplainer()
    explainers = XAIExplainerRegistry()
    explainers.register(UnavailableExplainer())
    explainers.register(explainer)
    payload = asyncio.run(
        _run_stage(
            tmp_path,
            _stub_detection_payload(),
            explainers=explainers,
            detectors=registry,
        )
    )
    assert payload["status"] == "COMPLETED"
    assert payload["explainer"]["technique"] == "grad-cam"
    assert payload["model"]["name"] == "stub-model"
    assert payload["heatmap"]["available"] is True
    assert payload["heatmap"]["format"] == "png"
    assert payload["heatmap"]["reference"] == "heatmaps/stub.png"
    assert payload["interpretation"]["target_label"] == "FAKE"
    assert payload["interpretation"]["target_score"] == 0.87
    assert payload["interpretation"]["score_semantics"] == "sigmoid probability"
    assert len(explainer.explained) == 1
    ctx = explainer.explained[0]
    assert ctx.detector is detector
    assert ctx.detection.prediction is not None
    assert ctx.device == "cpu"


def test_stage_rejects_video_media(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(
            _run_stage(
                tmp_path,
                _default_detection_payload(),
                content=b"not an image",
                media_type=MediaType.VIDEO,
            )
        )


def test_stage_missing_file(tmp_path: Path) -> None:
    stage, scan = XAIStage(), _scan_with_detection(_default_detection_payload())
    ctx = _ctx(tmp_path, _media(storage_path="ghost.png"), scan=scan)
    with pytest.raises(StageError, match="stored media file is missing"):
        asyncio.run(stage.run(ctx))


def test_stage_explainer_failure_is_client_safe(tmp_path: Path) -> None:
    detectors = DetectorRegistry()
    detectors.register(StubDetector())
    explainers = XAIExplainerRegistry()
    explainers.register(UnavailableExplainer())
    explainers.register(FailingExplainer())
    with pytest.raises(StageError, match="simulated explanation failure"):
        asyncio.run(
            _run_stage(
                tmp_path,
                _stub_detection_payload(),
                explainers=explainers,
                detectors=detectors,
            )
        )


def test_result_ref_structure(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _default_detection_payload()))
    assert set(payload) == {
        "status", "reason", "explainer", "model", "heatmap", "interpretation",
    }
    assert set(payload["explainer"]) == {"name", "version", "technique", "model_type"}
    assert set(payload["model"]) == {"name", "version", "checkpoint_sha256"}


def test_result_ref_deterministic(tmp_path: Path) -> None:
    stage = XAIStage()
    path, name = _write(tmp_path)
    ctx = _ctx(
        tmp_path,
        _media(storage_path=name),
        scan=_scan_with_detection(_default_detection_payload()),
    )
    first = asyncio.run(stage.run(ctx))
    second = asyncio.run(stage.run(ctx))
    assert first is not None and second is not None
    assert first.result_ref == second.result_ref


# --------------------------------------------------------------------------- #
# Pipeline integration
# --------------------------------------------------------------------------- #

async def test_worker_xai_stage_completed_unavailable(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path, filename="x.png", content=_png_bytes())
    worker = _worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["xai"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["xai"].result_ref or "{}")
    assert payload["status"] == "UNAVAILABLE"
    assert payload["heatmap"] is None
    assert by_name["detect"].status is StageStatus.COMPLETED
    detect_payload = json.loads(by_name["detect"].result_ref or "{}")
    assert detect_payload["inference"]["status"] == "UNAVAILABLE"


async def test_worker_xai_stage_completed_with_stub_explainer(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    detector = StubDetector()
    detectors = DetectorRegistry()
    detectors.register(detector)
    explainer = GradCAMLikeExplainer()
    explainers = XAIExplainerRegistry()
    explainers.register(UnavailableExplainer())
    explainers.register(explainer)
    queued = await _queued_scan(db_session, tmp_path, filename="y.png", content=_png_bytes())
    worker = _worker(
        tmp_path,
        detect=DetectionStage(detectors=detectors),
        xai=XAIStage(explainers=explainers, detectors=detectors),
    )

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["xai"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["xai"].result_ref or "{}")
    assert payload["status"] == "COMPLETED"
    assert payload["heatmap"]["available"] is True
    assert len(explainer.explained) == 1
    assert explainer.explained[0].detector is detector
