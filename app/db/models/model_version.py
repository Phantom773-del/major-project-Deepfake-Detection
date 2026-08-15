"""ModelVersion: a registered AI/ML model version used by the platform."""

from typing import Any

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.taxonomy import ModelVersionStatus


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A specific, identifiable version of a model.

    Multiple versions of the same model name may coexist; each (name, version)
    pair must be unique. No accuracy or capability claims are stored here
    unless experimentally verified by a later milestone.
    """

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_versions_name_version"),
    )

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    framework: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[ModelVersionStatus] = mapped_column(
        Enum(ModelVersionStatus, name="model_version_status"),
        nullable=False,
        default=ModelVersionStatus.ACTIVE,
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
