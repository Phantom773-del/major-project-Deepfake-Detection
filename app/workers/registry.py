"""StageRegistry: ordered name-to-stage mapping for the pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.workers.stages.base import Stage


class StageRegistry:
    """Ordered name-to-stage mapping. A stage name can be registered once."""

    def __init__(self) -> None:
        self._stages: dict[str, Stage] = {}

    def register(self, stage: Stage) -> None:
        if stage.name in self._stages:
            raise ValueError(f"stage already registered: {stage.name}")
        self._stages[stage.name] = stage

    def get(self, name: str) -> Stage | None:
        return self._stages.get(name)

    def names(self) -> list[str]:
        return list(self._stages)

    def __contains__(self, name: object) -> bool:
        return name in self._stages
