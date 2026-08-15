"""Media API schemas.

Media records are created exclusively via the secure upload endpoint. The
storage reference is internal and never exposed on read responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.taxonomy import MediaType


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
