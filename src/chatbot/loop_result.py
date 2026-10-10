"""What a run of the loop produced: its steps, their results and what they cost."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias

from anthropic.types import ContentBlock, MessageParam, TextBlock, ToolUseBlock


@dataclass(frozen=True)
class TokenUsage:
    token_count: int = 0

    def __add__(self, other: object) -> "TokenUsage":
        if not isinstance(other, TokenUsage):
            return NotImplemented

        return TokenUsage(self.token_count + other.token_count)


class StopReason(str, Enum):
    """Why the model stopped generating.

    A subset of the API's stop reasons: the ones the loop knows how to act on.
    NOTE anything else fails loudly when constructed rather than being mishandled.
    """

    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"


@dataclass(frozen=True)
class ModelResult:
    """One exchange with the model: a message sent and the reply received."""

    stop_reason: StopReason
    content: list[ContentBlock]
    sent: MessageParam
    received: MessageParam

    @property
    def messages(self) -> list[MessageParam]:
        """What this exchange added to the conversation, in order."""
        return [self.sent, self.received]

    @property
    def tool_calls(self) -> list[ToolUseBlock]:
        return [block for block in self.content if isinstance(block, ToolUseBlock)]

    @property
    def text(self) -> str:
        """The prose the model produced, without the tool-call blocks."""
        return "".join(
            block.text for block in self.content if isinstance(block, TextBlock)
        )


@dataclass(frozen=True)
class ToolResult:
    """What the tools produced, ready to be fed back to the model."""

    tool_result_message: MessageParam
    messages: list[MessageParam] = field(default_factory=list)


StepResult: TypeAlias = ModelResult | ToolResult

Trajectory: TypeAlias = list[StepResult]


def conversation_history(trajectory: Trajectory) -> list[MessageParam]:
    """The messages a trajectory put on the wire, in order."""
    return [message for result in trajectory for message in result.messages]


@dataclass(frozen=True)
class LoopOutcome:
    """Everything one run of the loop produced."""

    trajectory: Trajectory
    usage: TokenUsage

    @property
    def answer(self) -> str:
        """What to say back, with the narrowing done once rather than by callers.

        Empty if the run ended on a tool step, which is_done rules out.
        """
        result = self.result

        return result.text if isinstance(result, ModelResult) else ""

    @property
    def result(self) -> StepResult:
        """The step that ended the run."""
        return self.trajectory[-1]
