"""Base skill interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Skill(ABC, Generic[InputT, OutputT]):
    """A reusable, schema-bound capability invoked by an Agent."""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, input_data: InputT) -> OutputT:
        """Execute the skill and return a structured output."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
        }
