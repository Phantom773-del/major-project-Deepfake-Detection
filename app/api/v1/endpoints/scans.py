"""Scan endpoints: case record creation, retrieval and listing.

No AI analysis starts from these endpoints. Scan status is only changed through
the scan lifecycle service.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.domain.taxonomy import ScanStatus
from app.schemas.common import Envelope, Meta, Pagination
from app.schemas.scan import ScanCreate, ScanDetail, ScanRead
from app.services.scans import ScanService

router = APIRouter(prefix="/scans", tags=["scans"])


def _scan_service(session: AsyncSession = Depends(get_db)) -> ScanService:
    return ScanService(session)


def _pagination_meta(page: int, page_size: int, total: int) -> Meta:
    pages = (total + page_size - 1) // page_size
    return Meta(pagination=Pagination(page=page, page_size=page_size, total=total, pages=pages))


@router.post(
    "",
    response_model=Envelope[ScanDetail],
    status_code=status.HTTP_201_CREATED,
)
async def create_scan(
    payload: ScanCreate,
    service: ScanService = Depends(_scan_service),
) -> Envelope[ScanDetail]:
    scan = await service.create_scan(media_id=payload.media_id)
    await service.session.commit()
    scan = await service.get_scan(scan_id=scan.id)
    return Envelope[ScanDetail](data=ScanDetail.model_validate(scan))


@router.get(
    "/{scan_id}",
    response_model=Envelope[ScanDetail],
)
async def get_scan(
    scan_id: uuid.UUID,
    service: ScanService = Depends(_scan_service),
) -> Envelope[ScanDetail]:
    scan = await service.get_scan(scan_id=scan_id)
    return Envelope[ScanDetail](data=ScanDetail.model_validate(scan))


@router.get(
    "",
    response_model=Envelope[list[ScanRead]],
)
async def list_scans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    scan_status: ScanStatus | None = Query(default=None, alias="status"),
    service: ScanService = Depends(_scan_service),
) -> Envelope[list[ScanRead]]:
    items, total = await service.list_scans(
        page=page, page_size=page_size, status=scan_status
    )
    return Envelope[list[ScanRead]](
        data=[ScanRead.model_validate(item) for item in items],
        meta=_pagination_meta(page, page_size, total),
    )
