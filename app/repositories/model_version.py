"""ModelVersion repository."""

from sqlalchemy import select

from app.db.models.model_version import ModelVersion
from app.domain.taxonomy import ModelVersionStatus
from app.repositories.base import Repository


class ModelVersionRepository(Repository[ModelVersion]):
    model = ModelVersion

    async def list_all(
        self, *, status: ModelVersionStatus | None = None
    ) -> list[ModelVersion]:
        stmt = select(ModelVersion).order_by(ModelVersion.name, ModelVersion.version)
        if status is not None:
            stmt = stmt.where(ModelVersion.status == status)
        return list((await self.session.scalars(stmt)).all())

    async def list_active(self) -> list[ModelVersion]:
        return await self.list_all(status=ModelVersionStatus.ACTIVE)

    async def get_by_name_version(self, name: str, version: str) -> ModelVersion | None:
        stmt = select(ModelVersion).where(
            ModelVersion.name == name, ModelVersion.version == version
        )
        result = await self.session.scalar(stmt)
        if result is None:
            return None
        return result
