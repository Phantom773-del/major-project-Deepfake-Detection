"""ModelVersion API schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.taxonomy import ModelVersionStatus


class ModelVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=64)
    task: str = Field(min_length=1, max_length=64)
    framework: str | None = Field(default=None, max_length=64)
    status: ModelVersionStatus = ModelVersionStatus.ACTIVE


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    task: str
    framework: str | None
    status: ModelVersionStatus
    created_at: datetime
