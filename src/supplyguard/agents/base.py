"""Base agent interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Agent(ABC):
    """An agent in the SupplyGuard system."""

    name: str = ""
    role: str = ""
    skills: list[str]

    def __init__(self, runtime: Any | None = None) -> None:
        self.runtime = runtime
        self._skill_instances: dict[str, Any] = {}

    @abstractmethod
    async def handle(self, message: BaseModel) -> BaseModel | None:
        """Process an incoming message and optionally return a reply."""

    def identity(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "skills": self.skills,
        }
