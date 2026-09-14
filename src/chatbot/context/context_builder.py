from src.chatbot.context.block_type import BlockType
from src.chatbot.context.context_block import ContextBlock


class ContextBuilder:
    def __init__(self, blocks: list[ContextBlock]):
        self.blocks = blocks

    def _get_block(self, block_type: BlockType) -> ContextBlock:
        block = next((b for b in self.blocks if b.block_type == block_type), None)

        if not block:
            raise ValueError(f"Context block of type '{block_type.value}' not found")

        return block

    def get_system_prompt(self, **kwargs) -> str:
        return self._get_block(BlockType.SYSTEM).render(**kwargs)

    def get_tools_context(self, **kwargs) -> str:
        return self._get_block(BlockType.TOOLS).render(**kwargs)

    def build_context(self, **kwargs) -> str:
        return "\n\n".join(block.render(**kwargs) for block in self.blocks)
