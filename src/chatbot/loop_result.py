"""What a run of the loop produced: its steps, their results and what they cost."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, TypeAlias, TypeGuard

from anthropic.types import ContentBlock, MessageParam, TextBlock, ToolUseBlock

from src.chatbot.approval import PendingAction


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

    #: Deliberately empty. get_next_step hands
    #: tool_result_message to the following ModelStep, so it reaches the
    #: conversation as that step's `sent`. Listing it here as well would put
    #: every tool result into the history twice.
    messages: list[MessageParam] = field(default_factory=list)


@dataclass(frozen=True)
class ApprovalRequired:
    pending: list[PendingAction]

    #: Empty for the same reason a turn can resume at all: the message holding these
    #  tool calls is already in the history
    messages: list[MessageParam] = field(default_factory=list)


StepResult: TypeAlias = ModelResult | ToolResult | ApprovalRequired

Trajectory: TypeAlias = list[StepResult]


def is_awaiting_approval(result: StepResult) -> TypeGuard[ApprovalRequired]:
    """Whether this step handed the turn back to the user."""
    return isinstance(result, ApprovalRequired)


class Recorded(Protocol):
    """What every StepResult owes the history: the messages it put on the wire.

    Stated as a protocol so a new result type is made to declare it rather
    than discovering at runtime that conversation_history skipped it.
    """

    @property
    def messages(self) -> list[MessageParam]: ...


def conversation_history(trajectory: Iterable[Recorded]) -> list[MessageParam]:
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

    @property
    def pending(self) -> list[PendingAction]:
        """The actions waiting on the user, empty unless the run stopped for them."""
        result = self.result

        return result.pending if is_awaiting_approval(result) else []
