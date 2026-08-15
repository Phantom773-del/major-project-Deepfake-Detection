"""Health endpoint: liveness probe for the service."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import Envelope
from app.schemas.health import HealthResponse

router = APIRouter(tags=["meta"])

_settings = get_settings()


@router.get("/health", response_model=Envelope[HealthResponse], summary="Service liveness")
async def health() -> Envelope[HealthResponse]:
    """Return service identity and status. Independent of future subsystems."""
    return Envelope(
        data=HealthResponse(
            status="ok",
            service=_settings.app_name,
            version=_settings.app_version,
            api_version=_settings.api_v1_prefix,
        )
    )
