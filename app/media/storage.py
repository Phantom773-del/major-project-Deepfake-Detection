"""Storage abstraction for uploaded media.

The MediaService talks to a ``StorageProvider``; swapping the local filesystem
implementation for object storage later requires no media-domain changes.

Stored references are server-generated safe names. Never build a path from a
client-supplied filename.
"""

import os
from pathlib import Path
from typing import Protocol

from app.domain.exceptions import MediaUploadError


class StorageProvider(Protocol):
    """Persistence of uploaded media outside the database."""

    def persist(self, source: Path, *, name: str) -> str:
        """Move ``source`` into storage under the generated ``name``.

        Returns the internal storage reference (server-relative, safe).
        """
        ...

    def delete(self, ref: str) -> None:
        """Best-effort removal of a stored file by reference."""
        ...


class LocalStorageProvider:
    """Filesystem implementation rooted at a configurable directory."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def resolve(self, ref: str) -> Path:
        """Resolve a reference to an absolute path, rejecting traversal."""
        name = Path(ref).name
        if name != ref:
            raise MediaUploadError("invalid storage reference", code="INVALID_FILENAME")
        return self.root / name

    def persist(self, source: Path, *, name: str) -> str:
        if name != Path(name).name:
            raise MediaUploadError("invalid storage name", code="INVALID_FILENAME")
        self.root.mkdir(parents=True, exist_ok=True)
        os.replace(source, self.root / name)
        return name

    def delete(self, ref: str) -> None:
        path = self.resolve(ref)
        path.unlink(missing_ok=True)
