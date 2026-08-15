"""Media ingestion endpoint.

Thin route: delegates the whole workflow to MediaService. Only the real secure
upload endpoint exists; the temporary metadata-creation endpoint was removed.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.config import get_settings
from app.media.storage import LocalStorageProvider
from app.schemas.common import Envelope
from app.schemas.media import MediaRead
from app.services.media import MediaService

router = APIRouter(prefix="/media", tags=["media"])

_settings = get_settings()


def _media_service() -> MediaService:
    storage = LocalStorageProvider(Path(_settings.media_storage_root))
    return MediaService(storage)


@router.post(
    "/upload",
    response_model=Envelope[MediaRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a media file",
)
async def upload_media(
    file: UploadFile = File(...),
    service: MediaService = Depends(_media_service),
) -> Envelope[MediaRead]:
    media = await service.create_from_upload(file=file)
    return Envelope[MediaRead](data=MediaRead.model_validate(media))
