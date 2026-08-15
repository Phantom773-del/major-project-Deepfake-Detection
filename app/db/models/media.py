"""Media: persistent representation of uploaded media (metadata only)."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.taxonomy import MediaType


class Media(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Metadata record for an uploaded media object.

    Binary content is never stored in PostgreSQL; ``storage_path`` is a secure
    storage reference. ``original_filename`` is recorded but never trusted as
    authoritative. ``sha256`` enables duplicate detection.
    """

    __tablename__ = "media"

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, name="media_type"), nullable=False
    )
    mime_type: Mapped[str | None] = mapped_column(String(127))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
