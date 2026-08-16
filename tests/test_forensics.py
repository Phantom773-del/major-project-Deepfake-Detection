"""Visual forensics tests: analyzer contract, registry, analyzers, stage.

Covers real numerical behavior with deterministic synthetic images. No
authenticity verdicts are asserted — only measurement properties (bounds,
relationships, determinism) and honest failure semantics.
"""

import asyncio
import json
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import EvidenceType, MediaType, ScanStatus, StageStatus
from app.forensics.analyzers import build_default_forensic_analyzer_registry
from app.forensics.analyzers.ela import ErrorLevelAnalyzer
from app.forensics.analyzers.frequency import FrequencyAnalyzer
from app.forensics.analyzers.noise import NoiseResidualAnalyzer
from app.forensics.base import ForensicAnalyzer, ForensicError
from app.forensics.image import validate_image_size
from app.forensics.registry import ForensicAnalyzerRegistry
from app.forensics.result import AnalyzerResult, build_forensic_payload
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
from app.workers.stages.detect import DetectionStage
from app.workers.stages.fingerprint import FingerprintStage
from app.workers.stages.forensics import VisualForensicsStage
from app.workers.stages.metadata import MetadataStage
from app.workers.stages.validate import ValidateStage
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

# --------------------------------------------------------------------------- #
# Synthetic image fixtures (deterministic, programmatic)
# --------------------------------------------------------------------------- #

def _uniform(size: int = 64, value: int = 128) -> bytes:
    array = np.full((size, size), value, dtype=np.uint8)
    return _png(array)


def _gradient(size: int = 64) -> bytes:
    ramp = np.linspace(0, 255, size).astype(np.uint8)
    array = np.tile(ramp, (size, 1))
    return _png(array)


def _checkerboard(size: int = 64, cell: int = 2) -> bytes:
    indices = np.indices((size, size))
    array = (((indices[0] // cell) + (indices[1] // cell)) % 2) * 255
    return _png(array.astype(np.uint8))


def _noisy(size: int = 64, seed: int = 42) -> bytes:
    rng = np.random.default_rng(seed)
    array = rng.integers(0, 256, size=(size, size), dtype=np.uint8)
    return _png(array)


def _jpeg(content: bytes, quality: int = 75) -> bytes:
    with Image.open(BytesIO(content)) as image:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality)
        return buffer.getvalue()


def _png(array: np.ndarray) -> bytes:
    buffer = BytesIO()
    Image.fromarray(array, mode="L").save(buffer, format="PNG")
    return buffer.getvalue()


def _garbage() -> bytes:
    return b"this is definitely not an image file"


def _write(tmp_path: Path, content: bytes) -> tuple[Path, str]:
    name = f"for-{uuid.uuid4().hex}.png"
    path = tmp_path / name
    path.write_bytes(content)
    return path, name


def _settings(**overrides: Any) -> Settings:
    return Settings(media_storage_root=Path("unused"), **overrides)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ctx(tmp_path: Path, media: Media, settings: Settings) -> StageContext:
    return StageContext(
        scan=Scan(media_id=uuid.uuid4()),
        media=media,
        storage=LocalStorageProvider(tmp_path),
        settings=settings,
    )


async def _run_stage(
    tmp_path: Path,
    content: bytes,
    *,
    analyzers: ForensicAnalyzerRegistry | None = None,
    settings: Settings | None = None,
    media_type: MediaType = MediaType.IMAGE,
    mime_type: str = "image/png",
) -> Any:
    path, name = _write(tmp_path, content)
    media = Media(
        original_filename=name,
        media_type=media_type,
        storage_path=name,
        mime_type=mime_type,
    )
    result = await VisualForensicsStage(
        analyzers=analyzers
    ).run(_ctx(tmp_path, media, settings or _settings()))
    assert result is not None and result.result_ref is not None
    return json.loads(result.result_ref)


def _analyze(
    analyzer: ForensicAnalyzer,
    tmp_path: Path,
    content: bytes,
    *,
    settings: Settings | None = None,
) -> AnalyzerResult:
    path, _ = _write(tmp_path, content)
    return analyzer.analyze(path, settings=settings or _settings())


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


class BrokenAnalyzer:
    """Test analyzer that always fails with a client-safe error."""

    media_type = MediaType.IMAGE
    version = "1"

    def __init__(self, name: str = "broken") -> None:
        self.name = name

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        raise ForensicError("simulated analyzer failure")


class CrashingAnalyzer:
    """Test analyzer that raises an unexpected (non-Forensic) exception."""

    media_type = MediaType.IMAGE
    version = "1"

    def __init__(self, name: str = "crashing") -> None:
        self.name = name

    def analyze(self, path: Path, *, settings: Settings) -> AnalyzerResult:
        raise RuntimeError("boom")


# --------------------------------------------------------------------------- #
# Architecture: contract, registry
# --------------------------------------------------------------------------- #

def test_analyzer_contract_shape() -> None:
    for analyzer in (ErrorLevelAnalyzer(), NoiseResidualAnalyzer(), FrequencyAnalyzer()):
        assert analyzer.name
        assert analyzer.media_type is MediaType.IMAGE
        assert analyzer.version


def test_registry_register_and_lookup() -> None:
    registry = ForensicAnalyzerRegistry()
    analyzer = ErrorLevelAnalyzer()
    registry.register(analyzer)
    assert registry.get("ela") is analyzer
    assert "ela" in registry
    assert registry.names() == ["ela"]
    assert len(registry) == 1


def test_registry_rejects_duplicate_analyzer() -> None:
    registry = ForensicAnalyzerRegistry()
    registry.register(ErrorLevelAnalyzer())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ErrorLevelAnalyzer())


def test_registry_for_media_type() -> None:
    registry = build_default_forensic_analyzer_registry()
    assert [a.name for a in registry.for_media_type(MediaType.IMAGE)] == [
        "ela",
        "noise",
        "frequency",
    ]
    assert registry.for_media_type(MediaType.VIDEO) == []


def test_default_registry_contains_all_analyzers() -> None:
    registry = build_default_forensic_analyzer_registry()
    assert registry.names() == ["ela", "noise", "frequency"]


# --------------------------------------------------------------------------- #
# ELA
# --------------------------------------------------------------------------- #

def test_ela_deterministic(tmp_path: Path) -> None:
    analyzer = ErrorLevelAnalyzer()
    first = _analyze(analyzer, tmp_path, _noisy())
    second = _analyze(analyzer, tmp_path, _noisy())
    assert first.measurements == second.measurements
    assert first.findings == second.findings


def test_ela_uniform_image_zero_error(tmp_path: Path) -> None:
    result = _analyze(ErrorLevelAnalyzer(), tmp_path, _uniform())
    assert result.status == "COMPLETED"
    assert result.measurements["mean_abs_error"] == 0.0
    assert result.measurements["max_error"] == 0
    assert result.measurements["error_ratio"] == 0.0


def test_ela_jpeg_recompression_behavior(tmp_path: Path) -> None:
    source = _jpeg(_noisy(), quality=70)
    result = _analyze(ErrorLevelAnalyzer(), tmp_path, source)
    uniform = _analyze(ErrorLevelAnalyzer(), tmp_path, _uniform())
    assert result.status == "COMPLETED"
    assert result.measurements["mean_abs_error"] >= uniform.measurements["mean_abs_error"]
    assert 0.0 <= result.measurements["error_ratio"] <= 1.0


def test_ela_measurement_bounds(tmp_path: Path) -> None:
    for content in (_noisy(), _gradient(), _jpeg(_gradient(), quality=60)):
        result = _analyze(ErrorLevelAnalyzer(), tmp_path, content)
        m = result.measurements
        assert 0.0 <= m["mean_abs_error"] <= 255.0
        assert 0 <= m["max_error"] <= 255
        assert 0.0 <= m["p95_error"] <= 255.0
        assert 0.0 <= m["p99_error"] <= 255.0
        assert 0.0 <= m["error_ratio"] <= 1.0
        assert m["p95_error"] <= m["p99_error"]


def test_ela_invalid_image_raises(tmp_path: Path) -> None:
    with pytest.raises(ForensicError, match="not a readable image"):
        _analyze(ErrorLevelAnalyzer(), tmp_path, _garbage())


# --------------------------------------------------------------------------- #
# Noise residual
# --------------------------------------------------------------------------- #

def test_noise_deterministic(tmp_path: Path) -> None:
    analyzer = NoiseResidualAnalyzer()
    first = _analyze(analyzer, tmp_path, _noisy())
    second = _analyze(analyzer, tmp_path, _noisy())
    assert first.measurements == second.measurements
    assert first.findings == second.findings


def test_noise_uniform_image_zero_residual(tmp_path: Path) -> None:
    result = _analyze(NoiseResidualAnalyzer(), tmp_path, _uniform())
    assert result.status == "COMPLETED"
    assert result.measurements["residual_std"] == 0.0
    assert result.measurements["residual_energy"] == 0.0
    assert result.measurements["nonzero_ratio"] == 0.0


def test_noise_noisy_image_has_higher_energy(tmp_path: Path) -> None:
    noisy = _analyze(NoiseResidualAnalyzer(), tmp_path, _noisy())
    uniform = _analyze(NoiseResidualAnalyzer(), tmp_path, _uniform())
    assert noisy.measurements["residual_std"] > uniform.measurements["residual_std"]
    assert noisy.measurements["residual_energy"] > uniform.measurements["residual_energy"]


def test_noise_measurement_validity(tmp_path: Path) -> None:
    result = _analyze(NoiseResidualAnalyzer(), tmp_path, _noisy())
    m = result.measurements
    assert m["residual_std"] >= 0.0
    assert m["residual_energy"] >= 0.0
    assert 0.0 <= m["p99_abs_residual"] <= 255.0
    assert 0.0 <= m["nonzero_ratio"] <= 1.0
    assert abs(float(m["residual_mean"])) <= 255.0


def test_noise_invalid_image_raises(tmp_path: Path) -> None:
    with pytest.raises(ForensicError, match="not a readable image"):
        _analyze(NoiseResidualAnalyzer(), tmp_path, _garbage())


# --------------------------------------------------------------------------- #
# Frequency
# --------------------------------------------------------------------------- #

def test_frequency_deterministic(tmp_path: Path) -> None:
    analyzer = FrequencyAnalyzer()
    first = _analyze(analyzer, tmp_path, _checkerboard())
    second = _analyze(analyzer, tmp_path, _checkerboard())
    assert first.measurements == second.measurements
    assert first.findings == second.findings


def test_frequency_low_frequency_image(tmp_path: Path) -> None:
    result = _analyze(FrequencyAnalyzer(), tmp_path, _gradient())
    assert result.measurements["low_energy_ratio"] > result.measurements["high_energy_ratio"]


def test_frequency_high_frequency_pattern(tmp_path: Path) -> None:
    result = _analyze(FrequencyAnalyzer(), tmp_path, _checkerboard())
    assert result.measurements["high_energy_ratio"] > result.measurements["low_energy_ratio"]


def test_frequency_measurement_validity(tmp_path: Path) -> None:
    result = _analyze(FrequencyAnalyzer(), tmp_path, _checkerboard())
    m = result.measurements
    for key in ("low_energy_ratio", "mid_energy_ratio", "high_energy_ratio"):
        assert 0.0 <= m[key] <= 1.0
    total = m["low_energy_ratio"] + m["mid_energy_ratio"] + m["high_energy_ratio"]
    assert abs(total - 1.0) < 1e-4
    assert 0.0 <= m["spectral_entropy"] <= 1.0


def test_frequency_uniform_image_measurements_are_zero(tmp_path: Path) -> None:
    result = _analyze(FrequencyAnalyzer(), tmp_path, _uniform())
    m = result.measurements
    assert m["low_energy_ratio"] == 0.0
    assert m["mid_energy_ratio"] == 0.0
    assert m["high_energy_ratio"] == 0.0
    assert m["spectral_entropy"] == 0.0
    path, _ = _write(tmp_path, _uniform())
    payload = build_forensic_payload([result], validate_image_size(path, max_pixels=4096))
    assert "-0.0" not in json.dumps(payload)


def test_frequency_invalid_image_raises(tmp_path: Path) -> None:
    with pytest.raises(ForensicError, match="not a readable image"):
        _analyze(FrequencyAnalyzer(), tmp_path, _garbage())


# --------------------------------------------------------------------------- #
# Image safety
# --------------------------------------------------------------------------- #

def test_forensics_pixel_cap_enforced(tmp_path: Path) -> None:
    path, _ = _write(tmp_path, _uniform(64))
    with pytest.raises(ForensicError, match="pixel limit"):
        validate_image_size(path, max_pixels=100)


def test_stage_pixel_cap_fails_scan(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="pixel limit"):
        asyncio.run(
            _run_stage(
                tmp_path, _uniform(64), settings=_settings(forensics_max_pixels=100)
            )
        )


# --------------------------------------------------------------------------- #
# Stage
# --------------------------------------------------------------------------- #

def test_stage_registered_after_detection() -> None:
    registry = build_default_registry()
    names = registry.names()
    assert "forensics" in registry
    assert names.index("detect") < names.index("forensics")
    assert STAGE_ORDER.index("forensics") == STAGE_ORDER.index("detect") + 1


def test_stage_order_matches_pipeline() -> None:
    registry = build_default_registry()
    implemented = registry.names()
    assert [name for name in STAGE_ORDER if name in registry] == implemented


def test_stage_missing_file(tmp_path: Path) -> None:
    media = Media(
        original_filename="ghost.png",
        media_type=MediaType.IMAGE,
        storage_path="ghost.png",
        mime_type="image/png",
    )
    with pytest.raises(StageError, match="stored media file is missing"):
        asyncio.run(VisualForensicsStage().run(_ctx(tmp_path, media, _settings())))


def test_stage_rejects_video(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="not supported"):
        asyncio.run(
            _run_stage(
                tmp_path, _uniform(), media_type=MediaType.VIDEO, mime_type="video/mp4"
            )
        )


def test_stage_rejects_garbage_image(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="not a readable image"):
        asyncio.run(_run_stage(tmp_path, _garbage()))


def test_stage_result_ref_structure(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _noisy()))
    assert set(payload) == {"image", "summary", "analyzers"}
    assert set(payload["image"]) == {"format", "width", "height", "mode"}
    assert payload["summary"] == {"analyzers": 3, "completed": 3, "failed": 0}
    assert set(payload["analyzers"]) == {"ela", "noise", "frequency"}
    for analyzer in payload["analyzers"].values():
        assert set(analyzer) == {
            "analyzer", "version", "status", "error",
            "parameters", "measurements", "findings",
        }
        assert analyzer["status"] == "COMPLETED"
        assert analyzer["error"] is None
        assert len(analyzer["findings"]) >= 2
        types = {f["evidence_type"] for f in analyzer["findings"]}
        assert types <= {e.value for e in EvidenceType}


def test_stage_deterministic_payload(tmp_path: Path) -> None:
    content = _noisy()
    first = asyncio.run(_run_stage(tmp_path, content))
    second = asyncio.run(_run_stage(tmp_path, content))
    assert first == second


def test_stage_analyzer_failure_is_isolated(tmp_path: Path) -> None:
    registry = ForensicAnalyzerRegistry()
    registry.register(ErrorLevelAnalyzer())
    registry.register(BrokenAnalyzer())
    registry.register(FrequencyAnalyzer())
    payload = asyncio.run(_run_stage(tmp_path, _noisy(), analyzers=registry))
    assert payload["summary"] == {"analyzers": 3, "completed": 2, "failed": 1}
    assert payload["analyzers"]["broken"]["status"] == "FAILED"
    assert payload["analyzers"]["broken"]["error"] == "simulated analyzer failure"
    assert payload["analyzers"]["broken"]["measurements"] == {}
    assert payload["analyzers"]["ela"]["status"] == "COMPLETED"
    assert payload["analyzers"]["frequency"]["status"] == "COMPLETED"


def test_stage_unexpected_analyzer_exception_is_isolated(tmp_path: Path) -> None:
    registry = ForensicAnalyzerRegistry()
    registry.register(CrashingAnalyzer())
    registry.register(NoiseResidualAnalyzer())
    payload = asyncio.run(_run_stage(tmp_path, _noisy(), analyzers=registry))
    assert payload["summary"] == {"analyzers": 2, "completed": 1, "failed": 1}
    assert payload["analyzers"]["crashing"]["status"] == "FAILED"
    assert payload["analyzers"]["crashing"]["error"] == "unexpected analyzer failure"
    assert payload["analyzers"]["noise"]["status"] == "COMPLETED"


def test_stage_all_analyzers_fail_completes_with_errors(tmp_path: Path) -> None:
    registry = ForensicAnalyzerRegistry()
    registry.register(BrokenAnalyzer())
    registry.register(CrashingAnalyzer(name="crashing-2"))
    payload = asyncio.run(_run_stage(tmp_path, _noisy(), analyzers=registry))
    assert payload["summary"] == {"analyzers": 2, "completed": 0, "failed": 2}
    for analyzer in payload["analyzers"].values():
        assert analyzer["status"] == "FAILED"
        assert analyzer["error"]


def test_stage_empty_registry_fails(tmp_path: Path) -> None:
    with pytest.raises(StageError, match="no forensic analyzers"):
        asyncio.run(
            _run_stage(tmp_path, _noisy(), analyzers=ForensicAnalyzerRegistry())
        )


def test_stage_runs_independently_of_detection(tmp_path: Path) -> None:
    payload = asyncio.run(_run_stage(tmp_path, _noisy()))
    assert payload["summary"]["completed"] == 3
    assert payload["analyzers"]["ela"]["measurements"]["error_ratio"] >= 0.0


# --------------------------------------------------------------------------- #
# Pipeline integration
# --------------------------------------------------------------------------- #

async def test_worker_forensics_completed_with_detection_unavailable(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path, filename="f.png", content=_noisy())
    worker = build_default_worker(Settings(media_storage_root=tmp_path))

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["detect"].status is StageStatus.COMPLETED
    detect_payload = json.loads(by_name["detect"].result_ref or "{}")
    assert detect_payload["inference"]["status"] == "UNAVAILABLE"
    assert by_name["forensics"].status is StageStatus.COMPLETED
    forensics_payload = json.loads(by_name["forensics"].result_ref or "{}")
    assert forensics_payload["summary"] == {"analyzers": 3, "completed": 3, "failed": 0}
    assert forensics_payload["analyzers"]["ela"]["status"] == "COMPLETED"
    assert forensics_payload["analyzers"]["frequency"]["status"] == "COMPLETED"


async def test_worker_forensics_analyzer_failure_still_completes(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    registry = StageRegistry()
    registry.register(ValidateStage())
    registry.register(FingerprintStage())
    registry.register(MetadataStage())
    registry.register(DetectionStage())
    analyzers = ForensicAnalyzerRegistry()
    analyzers.register(BrokenAnalyzer())
    analyzers.register(FrequencyAnalyzer())
    registry.register(VisualForensicsStage(analyzers=analyzers))
    execution = ScanExecutionService(
        registry=registry,
        settings=Settings(media_storage_root=tmp_path),
    )
    worker = AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=0.01,
    )
    queued = await _queued_scan(db_session, tmp_path, filename="f2.png", content=_noisy())

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    by_name = {s.name: s for s in scan.stages}
    assert by_name["forensics"].status is StageStatus.COMPLETED
    payload = json.loads(by_name["forensics"].result_ref or "{}")
    assert payload["summary"] == {"analyzers": 2, "completed": 1, "failed": 1}
    assert payload["analyzers"]["broken"]["status"] == "FAILED"
