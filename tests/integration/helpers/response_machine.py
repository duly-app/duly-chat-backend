import json
from pathlib import Path
from typing import TypeAlias, TypedDict

from anthropic.types import MessageParam, StopReason, TextBlockParam, ToolUseBlockParam

ResponseBlock: TypeAlias = TextBlockParam | ToolUseBlockParam


class UsageData(TypedDict):
    input_tokens: int
    output_tokens: int


class ResponseData(TypedDict):
    stop_reason: StopReason
    content: list[ResponseBlock]
    usage: UsageData


class Transition(TypedDict):
    input: MessageParam
    next_response: ResponseData


class NoMatchingTransition(Exception):
    def __init__(self, message_input: MessageParam):
        super().__init__(f"No transition defined for input: {message_input}")


class AmbiguousTransition(Exception):
    def __init__(self, message_input: MessageParam):
        super().__init__(f"Multiple transitions match input: {message_input}")


def tool_use_id(message: MessageParam) -> str | None:
    """The tool call a tool-result message answers, if it is one."""
    content = message.get("content")

    if not isinstance(content, list):
        return None

    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            return block.get("tool_use_id")

    return None


def matches(transition: Transition, message_input: MessageParam) -> bool:
    expected = transition["input"]
    expected_id = tool_use_id(expected)

    if expected_id is not None:
        return tool_use_id(message_input) == expected_id

    return expected == message_input


class ResponseMachine:
    """Replays canned Claude responses, keyed on the newest message of the request."""

    transitions: list[Transition]

    def __init__(self, responses_path: Path):
        self.transitions = self._parse_transitions(responses_path)

    def _parse_transitions(self, path: Path) -> list[Transition]:
        with path.open("r") as f:
            return json.load(f)

    def next_response(self, message_input: MessageParam) -> ResponseData:
        matches_found = [t for t in self.transitions if matches(t, message_input)]

        if not matches_found:
            raise NoMatchingTransition(message_input)

        if len(matches_found) > 1:
            raise AmbiguousTransition(message_input)

        return matches_found[0]["next_response"]
