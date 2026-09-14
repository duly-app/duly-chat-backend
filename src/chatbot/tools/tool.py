from abc import ABC, abstractmethod
from typing import Any, ClassVar

from anthropic.types import ToolParam

from src.domain.user import Token, UserID


class Tool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]

    def __init__(self, user_id: UserID, thread_id: str, jwt: Token):
        self.user_id = user_id
        self.thread_id = thread_id
        self.jwt = jwt

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        for attr in ("name", "description", "input_schema"):
            if not getattr(cls, attr, None):
                raise ValueError(f"{cls.__name__} must define {attr}")

    @classmethod
    def schema(cls) -> ToolParam:
        return {
            "name": cls.name,
            "description": cls.description,
            "input_schema": cls.input_schema,
        }

    @abstractmethod
    def run(self, **tool_input: Any) -> str:
        """Do the work and render the outcome for the model to read."""
        raise NotImplementedError
