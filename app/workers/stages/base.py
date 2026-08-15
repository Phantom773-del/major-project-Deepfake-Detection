"""Stage abstraction for the analysis pipeline.

A stage has a stable name, an execution method, and a failure contract
(raise ``StageError`` with a client-safe message). Stages never touch the
database directly — the ``PipelineRunner`` owns stage-row status transitions.
"""

from dataclasses import dataclass
from typing import Protocol

from app.core.config import Settings
from app.db.models.media import Media
from app.db.models.scan import Scan
from app.media.storage import StorageProvider


class StageError(Exception):
    """Sanitized, client-safe failure message from a pipeline stage."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class StageResult:
    """Optional artifact a stage writes back to its ``ScanStage.result_ref``."""

    result_ref: str | None = None


@dataclass(frozen=True)
class StageContext:
    """Everything a stage is allowed to touch during one scan execution."""

    scan: Scan
    media: Media
    storage: StorageProvider
    settings: Settings


class Stage(Protocol):
    """One analysis pipeline stage."""

    name: str

    async def run(self, ctx: StageContext) -> StageResult | None:
        """Execute the stage. Raise ``StageError`` on failure."""
        ...
