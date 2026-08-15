"""Core domain persistence models.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate sees the full schema.
"""

from app.db.models.media import Media
from app.db.models.model_version import ModelVersion
from app.db.models.scan import Scan, ScanStage

__all__ = ["Media", "ModelVersion", "Scan", "ScanStage"]
