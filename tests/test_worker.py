"""Analysis worker + pipeline runner tests (real PostgreSQL, tmp storage)."""

import asyncio
import json
import uuid
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan
from app.db.session import SessionFactory
from app.domain.exceptions import ConflictError
from app.domain.scan import STAGE_ORDER
from app.domain.taxonomy import MediaType, ScanStatus, StageStatus
from app.media.hashing import sha256_of_bytes
from app.repositories.media import MediaRepository
from app.repositories.scan import ScanRepository
from app.services.execution import ScanExecutionService
from app.services.scans import ScanService
from app.workers.queue import AnalysisWorker, build_default_worker
from app.workers.registry import StageRegistry
from app.workers.stages import build_default_registry
from app.workers.stages.validate import ValidateStage
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession


def _png_bytes(width: int = 12, height: int = 9) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (120, 40, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _make_worker(tmp_path: Path) -> AnalysisWorker:
    execution = ScanExecutionService(
        registry=build_default_registry(),
        settings=Settings(media_storage_root=tmp_path),
    )
    return AnalysisWorker(
        session_factory=SessionFactory,
        execution=execution,
        poll_interval=0.01,
    )


async def _queued_scan(
    db_session: AsyncSession,
    tmp_path: Path,
    *,
    filename: str = "ref-a.png",
    content: bytes | None = None,
    write_file: bool = True,
    sha256_override: str | None = None,
) -> Scan:
    content = content if content is not None else _png_bytes()
    if write_file:
        (tmp_path / filename).write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename=filename,
            media_type=MediaType.IMAGE,
            storage_path=filename,
            mime_type="image/png",
            size_bytes=len(content),
            sha256=sha256_override if sha256_override is not None else sha256_of_bytes(content),
            width=12,
            height=9,
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


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_default_registry_has_only_implemented_stages() -> None:
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
    assert "metadata" in registry
    assert registry.get("detect") is not None
    assert registry.get("forensics") is not None
    assert registry.get("xai") is not None
    assert registry.get("evidence") is not None
    assert registry.get("confidence") is not None
    assert registry.get("risk") is not None
    assert registry.get("verdict") is not None


def test_registry_rejects_duplicate_registration() -> None:
    registry = StageRegistry()
    registry.register(ValidateStage())
    with pytest.raises(ValueError):
        registry.register(ValidateStage())


def test_pipeline_order_matches_stage_order() -> None:
    registry = build_default_registry()
    implemented = registry.names()
    assert [name for name in STAGE_ORDER if name in registry] == implemented


# --------------------------------------------------------------------------- #
# Worker end-to-end
# --------------------------------------------------------------------------- #

async def test_worker_processes_queued_scan_to_completed(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path)
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 1

    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.COMPLETED
    assert scan.completed_at is not None

    by_name = {s.name: s for s in scan.stages}
    assert by_name["validate"].status is StageStatus.COMPLETED
    assert by_name["validate"].duration_ms is not None
    assert by_name["fingerprint"].status is StageStatus.COMPLETED
    assert by_name["fingerprint"].result_ref is not None
    assert by_name["metadata"].status is StageStatus.COMPLETED
    assert by_name["metadata"].result_ref is not None
    assert by_name["detect"].status is StageStatus.COMPLETED
    assert by_name["detect"].result_ref is not None
    assert by_name["forensics"].status is StageStatus.COMPLETED
    assert by_name["forensics"].result_ref is not None
    assert by_name["xai"].status is StageStatus.COMPLETED
    assert by_name["xai"].result_ref is not None
    assert by_name["evidence"].status is StageStatus.COMPLETED
    assert by_name["evidence"].result_ref is not None
    assert by_name["confidence"].status is StageStatus.COMPLETED
    assert by_name["confidence"].result_ref is not None
    assert by_name["risk"].status is StageStatus.COMPLETED
    assert by_name["risk"].result_ref is not None
    assert by_name["verdict"].status is StageStatus.COMPLETED
    assert by_name["verdict"].result_ref is not None
    assert by_name["report"].status is StageStatus.COMPLETED
    assert by_name["report"].result_ref is not None


async def test_fingerprint_result_is_real(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    content = _png_bytes()
    queued = await _queued_scan(db_session, tmp_path, content=content)
    worker = _make_worker(tmp_path)
    await worker.run_until_idle()

    scan = await _reload(db_session, queued.id)
    fingerprint = next(s for s in scan.stages if s.name == "fingerprint")
    payload = json.loads(fingerprint.result_ref or "{}")
    assert payload["sha256"] == sha256_of_bytes(content)
    assert payload["size_bytes"] == len(content)
    assert len(payload["d_hash"]) == 16
    int(payload["d_hash"], 16)


async def test_worker_idle_returns_zero(db_session: AsyncSession, tmp_path: Path) -> None:
    assert await _make_worker(tmp_path).run_until_idle() == 0


async def test_worker_ignores_non_queued_scans(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    content = _png_bytes()
    (tmp_path / "ref-b.png").write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename="ref-b.png",
            media_type=MediaType.IMAGE,
            storage_path="ref-b.png",
            sha256=sha256_of_bytes(content),
        )
    )
    scan = await ScanService(db_session).create_scan(media_id=media.id)
    await db_session.commit()

    worker = _make_worker(tmp_path)
    assert await worker.run_until_idle() == 0
    loaded = await _reload(db_session, scan.id)
    assert loaded.status is ScanStatus.CREATED


async def test_worker_processes_each_scan_once(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    first = await _queued_scan(db_session, tmp_path, filename="one.png")
    second = await _queued_scan(db_session, tmp_path, filename="two.png")
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 2
    for scan in (first, second):
        loaded = await _reload(db_session, scan.id)
        assert loaded.status is ScanStatus.COMPLETED


async def test_concurrent_workers_never_double_process(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    first = await _queued_scan(db_session, tmp_path, filename="one.png")
    second = await _queued_scan(db_session, tmp_path, filename="two.png")
    worker_a = _make_worker(tmp_path)
    worker_b = _make_worker(tmp_path)

    counts = await asyncio.gather(
        worker_a.run_until_idle(), worker_b.run_until_idle()
    )
    assert sum(counts) == 2
    for scan in (first, second):
        loaded = await _reload(db_session, scan.id)
        assert loaded.status is ScanStatus.COMPLETED


async def test_worker_does_not_reclaim_processing_scan(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path)
    scan = await _reload(db_session, queued.id)
    await ScanService(db_session).transition(scan, to=ScanStatus.PROCESSING)
    await db_session.commit()

    worker = _make_worker(tmp_path)
    assert await worker.run_until_idle() == 0
    loaded = await _reload(db_session, queued.id)
    assert loaded.status is ScanStatus.PROCESSING


# --------------------------------------------------------------------------- #
# Failure paths
# --------------------------------------------------------------------------- #

async def test_worker_fails_scan_when_stored_file_missing(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path, write_file=False)
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.FAILED
    assert scan.error_message == "stored media file is missing"
    validate = next(s for s in scan.stages if s.name == "validate")
    assert validate.status is StageStatus.FAILED


async def test_worker_fails_scan_on_sha256_mismatch(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    other = _png_bytes(width=5, height=5)
    queued = await _queued_scan(
        db_session, tmp_path, sha256_override=sha256_of_bytes(other)
    )
    worker = _make_worker(tmp_path)

    assert await worker.run_until_idle() == 1
    scan = await _reload(db_session, queued.id)
    assert scan.status is ScanStatus.FAILED
    assert "sha256 mismatch" in (scan.error_message or "")
    validate = next(s for s in scan.stages if s.name == "validate")
    assert validate.status is StageStatus.FAILED


async def test_execution_requires_processing_state(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    content = _png_bytes()
    (tmp_path / "ref-c.png").write_bytes(content)
    media = await MediaRepository(db_session).create(
        Media(
            original_filename="ref-c.png",
            media_type=MediaType.IMAGE,
            storage_path="ref-c.png",
            sha256=sha256_of_bytes(content),
        )
    )
    scan = await ScanService(db_session).create_scan(media_id=media.id)
    await db_session.commit()

    execution = ScanExecutionService(
        registry=build_default_registry(),
        settings=Settings(media_storage_root=tmp_path),
    )
    with pytest.raises(ConflictError):
        await execution.execute(scan.id)


async def test_worker_handles_failure_without_crashing_loop(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    queued = await _queued_scan(db_session, tmp_path, write_file=False)
    worker = _make_worker(tmp_path)
    assert await worker.run_until_idle() == 1
    assert await worker.run_until_idle() == 0
    loaded = await _reload(db_session, queued.id)
    assert loaded.status is ScanStatus.FAILED


# --------------------------------------------------------------------------- #
# API integration: uploaded media -> scan -> worker -> completed
# --------------------------------------------------------------------------- #

async def test_api_scan_reaches_completed_via_worker(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    upload = await client.post(
        "/api/v1/media/upload",
        files={"file": ("scanme.png", _png_bytes(), "image/png")},
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
    data = detail.json()["data"]
    assert data["status"] == "COMPLETED"
    stages = {s["name"]: s for s in data["stages"]}
    assert stages["validate"]["status"] == "COMPLETED"
    assert stages["fingerprint"]["status"] == "COMPLETED"
    assert stages["metadata"]["status"] == "COMPLETED"
    assert stages["detect"]["status"] == "COMPLETED"
    assert stages["forensics"]["status"] == "COMPLETED"
    assert stages["xai"]["status"] == "COMPLETED"
    assert stages["xai"]["result_ref"] is not None
    assert stages["evidence"]["status"] == "COMPLETED"
    assert stages["evidence"]["result_ref"] is not None
    assert stages["confidence"]["status"] == "COMPLETED"
    assert stages["confidence"]["result_ref"] is not None
    assert stages["risk"]["status"] == "COMPLETED"
    assert stages["risk"]["result_ref"] is not None
    assert stages["verdict"]["status"] == "COMPLETED"
    assert stages["verdict"]["result_ref"] is not None
    assert stages["report"]["status"] == "COMPLETED"
    assert stages["report"]["result_ref"] is not None
