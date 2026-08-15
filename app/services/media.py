"""Media service: secure upload workflow.

Owns validation, fingerprinting, content detection, storage coordination and
Media record creation. The API route stays thin.

Failure ordering (documented in docs/BACKEND_IMPLEMENTATION.md §upload):
  1. validate filename
  2. stream upload to a temp file (enforcing size limit), hashing in one pass
  3. detect content (magic bytes + safe parse) and extract dimensions
  4. reject client extension/content mismatches
  5. persist temp file to storage under a generated safe name
  6. insert Media row and commit
  7. on commit failure: best-effort delete the stored file

Filesystem/PostgreSQL are not atomically consistent — the window between
persist and commit can leave an orphan if the process dies; cleanup covers
all handled failure paths.
"""

import asyncio
import hashlib
import os
import tempfile
import uuid
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile

from app.core.config import Settings, get_settings
from app.db.models.media import Media
from app.db.session import SessionFactory
from app.domain.exceptions import MediaUploadError
from app.media.detection import FORMAT_TO_EXTENSIONS, DetectedMedia, detect_image
from app.media.storage import StorageProvider

_CHUNK_SIZE = 64 * 1024
_MAX_FILENAME_LENGTH = 255
_UNSAFE_FILENAME_CHARS = {"\\", "/"}


class SessionFactoryProtocol(Protocol):
    """Anything callable returning an async session context manager."""

    def __call__(self) -> AbstractAsyncContextManager[Any]: ...


class MediaService:
    """Domain service for media ingestion."""

    def __init__(
        self,
        storage: StorageProvider,
        *,
        settings: Settings | None = None,
        session_factory: SessionFactoryProtocol | None = None,
    ) -> None:
        self.storage = storage
        self.settings = settings or get_settings()
        self._session_factory = session_factory or SessionFactory
        self._tmp_root = Path(self.settings.media_storage_root) / "tmp"

    async def create_from_upload(self, *, file: UploadFile) -> Media:
        """Ingest an uploaded file and create a verified Media record."""
        original_filename = _validated_filename(file.filename)

        tmp_path = self._new_tmp_path()
        try:
            size_bytes, sha256 = await _stream_to_tmp(file, tmp_path, self.settings)
            detected = await asyncio.to_thread(detect_image, tmp_path)

            _validate_extension(original_filename, detected.format)

            storage_ref = await asyncio.to_thread(
                self.storage.persist, tmp_path, name=_generated_name(detected)
            )

            media = Media(
                original_filename=original_filename,
                media_type=detected.media_type,
                mime_type=detected.mime_type,
                size_bytes=size_bytes,
                sha256=sha256,
                width=detected.width,
                height=detected.height,
                storage_path=storage_ref,
            )
            async with self._session_factory() as session:
                session.add(media)
                try:
                    await session.commit()
                except BaseException:
                    await asyncio.to_thread(self.storage.delete, storage_ref)
                    raise
            return media
        finally:
            tmp_path.unlink(missing_ok=True)

    def _new_tmp_path(self) -> Path:
        self._tmp_root.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix="upload-", dir=self._tmp_root)
        os.close(fd)
        return Path(name)


async def _stream_to_tmp(file: UploadFile, tmp_path: Path, settings: Settings) -> tuple[int, str]:
    """Stream upload to disk in chunks, enforcing the size limit and hashing once."""
    digest = hashlib.sha256()
    size = 0
    limit = settings.max_upload_size_bytes
    with tmp_path.open("wb") as out:
        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                raise MediaUploadError(
                    f"file exceeds maximum upload size ({settings.max_upload_size_mb} MB)",
                    code="FILE_TOO_LARGE",
                )
            digest.update(chunk)
            out.write(chunk)
    return size, digest.hexdigest()


def _validated_filename(filename: str | None) -> str:
    if not filename:
        raise MediaUploadError("missing filename", code="INVALID_FILENAME")
    name = Path(filename).name
    if name != filename or any(c in filename for c in _UNSAFE_FILENAME_CHARS):
        raise MediaUploadError("unsafe filename", code="INVALID_FILENAME")
    if len(name.encode("utf-8")) > _MAX_FILENAME_LENGTH:
        raise MediaUploadError("filename too long", code="INVALID_FILENAME")
    return name


def _validate_extension(filename: str, detected_format: str) -> None:
    suffix = Path(filename).suffix.lower()
    allowed = FORMAT_TO_EXTENSIONS[detected_format]
    if suffix not in allowed:
        raise MediaUploadError(
            f"filename extension does not match detected content ({detected_format})",
            code="INVALID_CONTENT",
        )


def _generated_name(detected: DetectedMedia) -> str:
    return f"{uuid.uuid4().hex}{detected.canonical_extension}"
