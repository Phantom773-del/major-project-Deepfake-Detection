"""Media ingestion and fingerprinting tests.

Security-focused: valid/invalid uploads, MIME/extension spoofing, path
traversal, fingerprint correctness, image metadata, failure cleanup.
"""

from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import Settings
from app.domain.exceptions import MediaUploadError
from app.media.hashing import sha256_of_bytes, sha256_of_file
from app.media.storage import LocalStorageProvider, StorageProvider
from app.repositories.media import MediaRepository
from app.services.media import MediaService
from fastapi import UploadFile
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers


def _image_bytes(
    fmt: str,
    width: int = 7,
    height: int = 5,
    color: tuple[int, int, int] = (0, 128, 255),
) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format=fmt)
    return buf.getvalue()


def _upload_file(
    *,
    filename: str = "a.png",
    content: bytes | None = None,
    content_type: str | None = None,
) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type else None
    return UploadFile(
        filename=filename,
        file=BytesIO(content if content is not None else _image_bytes("PNG")),
        headers=headers,
    )


class _SessionFactory:
    """AsyncSession-compatible session whose commit fails."""

    def add(self, obj: object) -> None:
        return None

    async def commit(self) -> None:
        raise RuntimeError("simulated database failure")

    async def __aenter__(self) -> _SessionFactory:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class _FailingStorage:
    """StorageProvider whose persist always fails."""

    def resolve(self, ref: str) -> Path:
        return Path(ref)

    def persist(self, source: Path, *, name: str) -> str:
        raise OSError("disk full")

    def delete(self, ref: str) -> None:
        return None


async def _make_service(tmp_path: Path, *, storage: StorageProvider | None = None) -> MediaService:
    return MediaService(
        storage or LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path),
    )


# --------------------------------------------------------------------------- #
# Valid uploads
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("fmt", "filename", "mime"),
    [
        ("JPEG", "photo.jpg", "image/jpeg"),
        ("PNG", "photo.png", "image/png"),
        ("WEBP", "photo.webp", "image/webp"),
    ],
)
async def test_valid_image_uploads(
    tmp_path: Path, fmt: str, filename: str, mime: str
) -> None:
    service = await _make_service(tmp_path)
    content = _image_bytes(fmt)
    media = await service.create_from_upload(file=_upload_file(filename=filename, content=content))

    assert media.media_type.value == "IMAGE"
    assert media.mime_type == mime
    assert media.size_bytes == len(content)
    assert media.sha256 == sha256_of_bytes(content)
    assert sha256_of_file(tmp_path / media.storage_path) == sha256_of_bytes(content)
    assert media.width == 7
    assert media.height == 5
    assert media.original_filename == filename
    assert Path(media.storage_path).name == media.storage_path


async def test_stored_file_uses_generated_safe_name(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    media = await service.create_from_upload(file=_upload_file(filename="whatever.png"))

    stored = tmp_path / media.storage_path
    assert stored.exists()
    assert stored.name != "whatever.png"
    assert stored.name.split(".")[0] == Path(media.storage_path).stem
    assert stored.name.endswith(".png")


# --------------------------------------------------------------------------- #
# Invalid uploads
# --------------------------------------------------------------------------- #

async def test_empty_file_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(content=b""))
    assert exc.value.code == "EMPTY_FILE"


async def test_random_bytes_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(content=b"\x00\x01\x02not an image"))
    assert exc.value.code == "INVALID_CONTENT"


async def test_malformed_image_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    malformed = _image_bytes("PNG")[:20] + b"\xff\xff\xffgarbage"  # png magic then junk
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(content=malformed))
    assert exc.value.code == "INVALID_CONTENT"


async def test_extension_spoofing_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(
            file=_upload_file(filename="fake.png", content=_image_bytes("JPEG"))
        )
    assert exc.value.code == "INVALID_CONTENT"


async def test_unsupported_content_type_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(
            file=_upload_file(filename="a.gif", content=_image_bytes("GIF"))
        )
    assert exc.value.code == "UNSUPPORTED_TYPE"


async def test_oversized_file_rejected(tmp_path: Path) -> None:
    service = MediaService(
        LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path, max_upload_size_mb=0),
    )
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(content=_image_bytes("PNG")))
    assert exc.value.code == "FILE_TOO_LARGE"


# --------------------------------------------------------------------------- #
# Security: filenames
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "filename",
    [
        "../../etc/passwd.png",
        "..\\..\\windows\\system32.png",
        "a/b/c.png",
    ],
)
async def test_path_traversal_filenames_rejected(tmp_path: Path, filename: str) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(filename=filename))
    assert exc.value.code == "INVALID_FILENAME"


async def test_very_long_filename_rejected(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    long_name = "x" * 300 + ".png"
    with pytest.raises(MediaUploadError) as exc:
        await service.create_from_upload(file=_upload_file(filename=long_name))
    assert exc.value.code == "INVALID_FILENAME"


async def test_unusual_but_safe_filename_accepted(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    media = await service.create_from_upload(file=_upload_file(filename="my photo (1)!.png"))
    assert media.original_filename == "my photo (1)!.png"


# --------------------------------------------------------------------------- #
# Fingerprint
# --------------------------------------------------------------------------- #

async def test_sha256_matches_independent_hash(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    content = _image_bytes("PNG")
    media = await service.create_from_upload(file=_upload_file(content=content))
    assert media.sha256 == sha256_of_bytes(content)


async def test_same_bytes_same_hash_different_bytes_different(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    a = await service.create_from_upload(file=_upload_file(content=_image_bytes("PNG")))
    b = await service.create_from_upload(file=_upload_file(content=_image_bytes("PNG")))
    c = await service.create_from_upload(
        file=_upload_file(content=_image_bytes("PNG", color=(1, 2, 3)))
    )
    assert a.sha256 == b.sha256  # duplicate policy: allowed, separate records
    assert a.id != b.id
    assert a.sha256 != c.sha256


# --------------------------------------------------------------------------- #
# Dimensions from server, never from client
# --------------------------------------------------------------------------- #

async def test_dimensions_detected_from_content(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    media = await service.create_from_upload(
        file=_upload_file(content=_image_bytes("PNG", 320, 240))
    )
    assert (media.width, media.height) == (320, 240)


# --------------------------------------------------------------------------- #
# Failure cleanup
# --------------------------------------------------------------------------- #

async def test_invalid_upload_leaves_no_files(tmp_path: Path) -> None:
    service = await _make_service(tmp_path)
    with pytest.raises(MediaUploadError):
        await service.create_from_upload(file=_upload_file(content=b"\x00not media"))
    assert _stored_files(tmp_path) == []


async def test_storage_failure_creates_no_media_row(
    tmp_path: Path, db_session: AsyncSession
) -> None:
    service = await _make_service(tmp_path, storage=_FailingStorage())
    with pytest.raises(OSError):
        await service.create_from_upload(file=_upload_file())
    items, _total = await MediaRepository(db_session).list_all(page=1, page_size=100)
    assert items == []
    assert _stored_files(tmp_path) == []


async def test_db_failure_after_storage_removes_stored_file(tmp_path: Path) -> None:
    service = MediaService(
        LocalStorageProvider(tmp_path),
        settings=Settings(media_storage_root=tmp_path),
        session_factory=_boom_factory(),
    )
    with pytest.raises(RuntimeError, match="simulated database failure"):
        await service.create_from_upload(file=_upload_file())
    assert _stored_files(tmp_path) == []


def _boom_factory() -> Callable[[], _SessionFactory]:
    return _SessionFactory


def _stored_files(root: Path) -> list[str]:
    return sorted(p.name for p in root.iterdir() if p.is_file())


# --------------------------------------------------------------------------- #
# API surface
# --------------------------------------------------------------------------- #

async def test_api_upload_mime_spoofing_uses_detected_type(client: AsyncClient) -> None:
    content = _image_bytes("JPEG")
    resp = await client.post(
        "/api/v1/media/upload",
        files={"file": ("photo.jpg", content, "image/png")},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["mime_type"] == "image/jpeg"
    assert data["original_filename"] == "photo.jpg"


async def test_api_upload_oversized_rejected(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.api.v1.endpoints.media as media_module

    monkeypatch.setattr(media_module._settings, "max_upload_size_mb", 0)
    resp = await client.post(
        "/api/v1/media/upload",
        files={"file": ("a.png", _image_bytes("PNG"), "image/png")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_api_upload_rejects_invalid_content(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/media/upload",
        files={"file": ("a.png", b"totally not an image", "image/png")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_CONTENT"


async def test_api_upload_no_internal_path_leakage(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/media/upload",
        files={"file": ("a.png", _image_bytes("PNG"), "image/png")},
    )
    assert resp.status_code == 201
    raw = resp.text
    assert "storage_path" not in raw
    assert raw is not None and "storage" not in raw


async def test_uploaded_media_supports_scan_creation(client: AsyncClient) -> None:
    media_resp = await client.post(
        "/api/v1/media/upload",
        files={"file": ("scanme.png", _image_bytes("PNG"), "image/png")},
    )
    media_id = media_resp.json()["data"]["id"]
    scan_resp = await client.post("/api/v1/scans", json={"media_id": media_id})
    assert scan_resp.status_code == 201
    assert scan_resp.json()["data"]["media_id"] == media_id
