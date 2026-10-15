from src.chatbot.context.context_block import ContextBlock


class ContextBuilder:
    def __init__(self, blocks: list[ContextBlock]):
        self.blocks = blocks

    def build_context(self, **kwargs) -> str:
        return "\n\n".join(block.render(**kwargs) for block in self.blocks)
