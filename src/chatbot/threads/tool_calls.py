from typing import Iterable

from anthropic.types import MessageParam, ToolUseBlock


def unanswered_tool_calls(messages: list[MessageParam]) -> list[ToolUseBlock]:
    """The calls at the end of a thread that have no results yet."""
    if not messages:
        return []

    last = messages[-1]

    if last.get("role") != "assistant":
        return []

    return [block for block in _blocks(last.get("content")) if block is not None]


def _blocks(content: object) -> Iterable[ToolUseBlock | None]:
    """Yield the tool use blocks from the content, if any."""
    if not isinstance(content, Iterable) or isinstance(content, str):
        return []

    return (_as_tool_use(block) for block in content)


def _as_tool_use(block: object) -> ToolUseBlock | None:
    """Tool calls survive as objects in memory and as dicts once serialised."""
    if isinstance(block, ToolUseBlock):
        return block

    if isinstance(block, dict) and block.get("type") == "tool_use":
        return ToolUseBlock.model_validate(block)

    return None
