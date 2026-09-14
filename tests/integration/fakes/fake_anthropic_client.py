from dataclasses import dataclass, field
from typing import Any

from anthropic.types import (
    ContentBlock,
    MessageParam,
    StopReason,
    TextBlock,
    ToolUseBlock,
    Usage,
)

from tests.integration.helpers.response_machine import (
    ResponseBlock,
    ResponseData,
    ResponseMachine,
)


@dataclass
class FakeMessage:
    """Only the attributes the loop reads off a real Message."""

    content: list[ContentBlock]
    stop_reason: StopReason
    usage: Usage


def _parse_block(data: ResponseBlock) -> ContentBlock:
    """Build the SDK's own block types."""
    # Narrowed on the literal so the type checker knows which TypedDict it has.
    if data["type"] == "tool_use":
        return ToolUseBlock(
            id=data["id"], name=data["name"], input=dict(data["input"]), type="tool_use"
        )

    return TextBlock(text=data["text"], type="text")


def _parse_message(data: ResponseData) -> FakeMessage:
    return FakeMessage(
        content=[_parse_block(block) for block in data["content"]],
        stop_reason=data["stop_reason"],
        usage=Usage(**data["usage"]),
    )


@dataclass
class FakeMessages:
    _machine: ResponseMachine
    calls: list[dict[str, Any]] = field(default_factory=list)

    def create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        last_message: MessageParam = kwargs["messages"][-1]

        return _parse_message(self._machine.next_response(last_message))


class FakeAnthropicClient:
    messages: FakeMessages

    def __init__(self, machine: ResponseMachine):
        self.messages = FakeMessages(machine)
