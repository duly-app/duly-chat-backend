from abc import ABC, abstractmethod
from typing import ClassVar

from src.chatbot.context.block_type import BlockType


class ContextBlock(ABC):
    block_type: ClassVar[BlockType]
    content: str | None
    sub_blocks: list["ContextBlock"] | None

    def __init__(
        self, content: str | None = None, sub_blocks: list["ContextBlock"] | None = None
    ):
        self.content = content
        self.sub_blocks = sub_blocks

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "block_type") or cls.block_type is None:
            raise ValueError(f"{cls.__name__} must define block_type")

    def render(self, **kwargs) -> str:
        if self.content is None:
            raise ValueError(
                f"Content for {self.block_type.value} block is not loaded."
            )

        return self._render(self.content, self.sub_blocks, **kwargs)

    def load_content(self, path: str) -> None:
        with open(path) as f:
            self.content = f.read()

    @abstractmethod
    def _render(
        self, content: str, sub_blocks: list["ContextBlock"] | None, **kwargs
    ) -> str:
        raise NotImplementedError


class SystemPromptBlock(ContextBlock):
    block_type = BlockType.SYSTEM

    def _render(
        self, content: str, sub_blocks: list["ContextBlock"] | None, **kwargs
    ) -> str:
        return content.format(**kwargs)
