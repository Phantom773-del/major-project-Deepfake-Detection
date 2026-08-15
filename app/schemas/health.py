"""Health endpoint schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness information returned by ``GET /api/v1/health``."""

    status: str
    service: str
    version: str
    api_version: str
