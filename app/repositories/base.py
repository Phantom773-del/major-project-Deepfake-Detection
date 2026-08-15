"""Generic repository base: shared persistence operations.

Concrete repositories subclass this and set ``model``. Keep repositories
persistence-only: no business rules here.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class Repository[T: Base]:
    """Minimal shared create/get persistence."""

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get(self, entity_id: uuid.UUID) -> T | None:
        return await self.session.get(self.model, entity_id)
