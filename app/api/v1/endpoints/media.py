"""Minimal media endpoints for the vertical slice.

The real secure upload workflow is a later milestone. This endpoint only creates
the persistence record referenced by scan creation.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.media import Media
from app.db.session import get_db
from app.repositories.media import MediaRepository
from app.schemas.common import Envelope
from app.schemas.media import MediaCreate, MediaRead

router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "",
    response_model=Envelope[MediaRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_media(
    payload: MediaCreate,
    session: AsyncSession = Depends(get_db),
) -> Envelope[MediaRead]:
    repo = MediaRepository(session)
    media = await repo.create(Media(**payload.model_dump()))
    await session.commit()
    return Envelope[MediaRead](data=MediaRead.model_validate(media))
