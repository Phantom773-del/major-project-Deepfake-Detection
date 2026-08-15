"""Scan and ScanStage API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.taxonomy import ScanStatus, StageStatus
from app.schemas.media import MediaRead


class ScanCreate(BaseModel):
    """Create a scan case record for an existing media object."""

    media_id: uuid.UUID


class ScanStageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_id: uuid.UUID
    name: str
    status: StageStatus
    sequence: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_message: str | None
    result_ref: str | None


class ScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_id: uuid.UUID
    status: ScanStatus
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime


class ScanDetail(ScanRead):
    media: MediaRead
    stages: list[ScanStageRead]


class ScanPage(BaseModel):
    items: list[ScanRead]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
