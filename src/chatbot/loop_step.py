"""The steps a run is made of: calling the model, and running the tools it asked for."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from anthropic import Anthropic
from anthropic.types import MessageParam, ToolResultBlockParam, ToolUseBlock

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.loop_result import (
    ModelResult,
    StepResult,
    StopReason,
    TokenUsage,
    ToolResult,
    Trajectory,
    conversation_history,
)
from src.chatbot.threads.thread_store import ThreadID, TurnID
from src.chatbot.tools.registry import ToolRegistry
from src.domain.user import Token, UserID

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4096


@dataclass
class LoopContext:
    user_id: UserID
    thread_id: ThreadID
    turn_id: TurnID
    jwt: Token
    history: list[MessageParam]
    trajectory: Trajectory
    api_adapter: "APIAdapter"
    anthropic_client: Anthropic
    context_builder: ContextBuilder
    tool_registry: ToolRegistry


class LoopStep(ABC):
    @abstractmethod
    def execute(self, context: LoopContext) -> tuple[StepResult, TokenUsage]:
        raise NotImplementedError()


class ModelStep(LoopStep):
    """Calls Claude with the conversation so far plus one new message."""

    message: MessageParam

    def __init__(self, message: MessageParam):
        self.message = message

    def execute(self, context: LoopContext) -> tuple[StepResult, TokenUsage]:
        response = context.anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=context.context_builder.build_context(),
            messages=[
                *context.history,
                *conversation_history(context.trajectory),
                self.message,
            ],
            tools=[tool.schema for tool in context.tool_registry.values()],
        )

        result = ModelResult(
            stop_reason=StopReason(response.stop_reason or "end_turn"),
            content=list(response.content),
            sent=self.message,
            received={"role": "assistant", "content": response.content},
        )

        usage = TokenUsage(
            token_count=response.usage.input_tokens + response.usage.output_tokens
        )

        return result, usage


class ActionStep(LoopStep):
    """Runs the tools the model asked for. Makes no model call, so costs no tokens."""

    tool_calls: list[ToolUseBlock]

    def __init__(self, tool_calls: list[ToolUseBlock]):
        self.tool_calls = tool_calls

    def execute(self, context: LoopContext) -> tuple[StepResult, TokenUsage]:
        blocks = [self._run(context, call) for call in self.tool_calls]

        # Tool results travel as content blocks inside a user message: the
        # Anthropic API has no "tool" role.
        message: MessageParam = {"role": "user", "content": blocks}

        return ToolResult(tool_result_message=message), TokenUsage()

    def _run(self, context: LoopContext, call: ToolUseBlock) -> ToolResultBlockParam:
        tool_maker = context.tool_registry.get(call.name)

        if tool_maker is None:
            return self._failed(call, f"No such tool: {call.name}")

        tool = tool_maker.create(context.user_id, context.thread_id, context.jwt)

        try:
            content = tool.run(**dict(call.input))
        except Exception as error:
            # Every tool failure is reported to the model rather than raised.
            # A broken tool is a fact about the world the model can act on —
            # explain it, try another route, or stop
            #
            # Only the exception's type, not its message: a requests error
            # carries the internal service URL
            return self._failed(call, f"{tool.error_response} ({type(error).__name__})")

        if not content:
            # The API rejects empty content blocks, so an empty return would
            # fail the turn at the API with nothing to point at.
            return self._failed(call, f"{call.name} returned nothing.")

        return {
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": content,
        }

    @staticmethod
    def _failed(call: ToolUseBlock, content: str) -> ToolResultBlockParam:
        return {
            "type": "tool_result",
            "tool_use_id": call.id,
            "content": content,
            "is_error": True,
        }
