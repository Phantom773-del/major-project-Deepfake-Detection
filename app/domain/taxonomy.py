"""Domain enumerations (statuses, types).

Enums live here (not in the models) so domain logic, schemas and API contracts
share one source of truth. Stored in PostgreSQL as native enums.
"""

import enum


class ScanStatus(enum.StrEnum):
    """Lifecycle states for a forensic scan (see ``app/domain/scan.py`` for transitions)."""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StageStatus(enum.StrEnum):
    """Per-stage pipeline state."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ModelVersionStatus(enum.StrEnum):
    """Lifecycle state of a registered model version."""

    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class MediaType(enum.StrEnum):
    """High-level category of uploaded media."""

    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    UNKNOWN = "UNKNOWN"
