"""Scan: central forensic case record, plus per-stage ScanStage rows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin
from app.db.models.media import Media
from app.domain.taxonomy import ScanStatus, StageStatus


class Scan(Base, UUIDPrimaryKeyMixin, UpdatedAtMixin):
    """One analysis request against one media object.

    Orchestration/case record only: pipeline results live in later-milestone
    tables keyed by scan. Status changes must go through the scan lifecycle
    service, which enforces the documented state machine.
    """

    __tablename__ = "scans"

    media_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media.id", ondelete="RESTRICT"), nullable=False
    )
    media: Mapped[Media] = relationship()

    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, name="scan_status"),
        nullable=False,
        default=ScanStatus.CREATED,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(500))

    stages: Mapped[list[ScanStage]] = relationship(
        back_populates="scan",
        cascade="all, delete-orphan",
        order_by="ScanStage.sequence",
    )


class ScanStage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single pipeline stage belonging to a scan.

    Stages are rows, not schema, so new pipeline stages can be added without a
    migration (see ``STAGE_ORDER`` in ``app/domain/scan.py``).
    """

    __tablename__ = "scan_stages"
    __table_args__ = (
        UniqueConstraint("scan_id", "name", name="uq_scan_stages_scan_id_name"),
    )

    scan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    scan: Mapped[Scan] = relationship(back_populates="stages")

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[StageStatus] = mapped_column(
        Enum(StageStatus, name="stage_status"),
        nullable=False,
        default=StageStatus.PENDING,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(String(500))
    result_ref: Mapped[str | None] = mapped_column(String(255))
