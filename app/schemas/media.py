"""Media API schemas.

Minimal representation for this milestone. The full secure upload workflow is a
later milestone; ``storage_path`` is required on create as the storage
reference and is deliberately NOT exposed on read responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.taxonomy import MediaType


class MediaCreate(BaseModel):
    original_filename: str = Field(min_length=1, max_length=255)
    media_type: MediaType
    storage_path: str = Field(min_length=1, max_length=512)
    mime_type: str | None = Field(default=None, max_length=127)
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    width: int | None = Field(default=None, ge=0)
    height: int | None = Field(default=None, ge=0)


class MediaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    media_type: MediaType
    mime_type: str | None
    size_bytes: int | None
    sha256: str | None
    width: int | None
    height: int | None
    is_deleted: bool
    created_at: datetime
