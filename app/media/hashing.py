"""Streaming SHA-256 fingerprinting.

Hashes the raw stored file bytes in chunks — never the decoded pixels, filename
or metadata. A SHA-256 match means identical file bytes, not identical visual
content.
"""

import hashlib
from pathlib import Path

_CHUNK_SIZE = 64 * 1024


def sha256_of_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of ``data`` (test/verification aid)."""
    return hashlib.sha256(data).hexdigest()
