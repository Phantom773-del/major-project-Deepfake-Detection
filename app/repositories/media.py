"""Media repository."""

from sqlalchemy import func, select

from app.db.models.media import Media
from app.repositories.base import Repository


class MediaRepository(Repository[Media]):
    model = Media

    async def list_all(self, *, page: int, page_size: int) -> tuple[list[Media], int]:
        active = Media.is_deleted.is_(False)
        total = await self.session.scalar(
            select(func.count(Media.id)).where(active)
        )
        stmt = (
            select(Media)
            .where(active)
            .order_by(Media.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.scalars(stmt)).all())
        return items, total if total is not None else 0
