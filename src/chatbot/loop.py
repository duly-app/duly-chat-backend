from anthropic import Anthropic

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.errors import MaxIterationsExceeded, ResponseTruncated
from src.chatbot.loop_result import (
    LoopOutcome,
    ModelResult,
    StepResult,
    StopReason,
    TokenUsage,
    ToolResult,
)
from src.chatbot.loop_step import ActionStep, LoopContext, LoopStep, ModelStep
from src.chatbot.tools.registry import ToolRegistry
from src.domain.user import Token, UserID


def chat_loop(
    user_id: UserID,
    thread_id: str,
    message: str,
    jwt: Token,
    api_adapter: "APIAdapter",
    anthropic_client: Anthropic,
    context_builder: ContextBuilder,
    tool_registry: ToolRegistry,
    max_iterations: int = 10,
) -> LoopOutcome:
    context = LoopContext(
        user_id=user_id,
        thread_id=thread_id,
        jwt=jwt,
        trajectory=[],
        api_adapter=api_adapter,
        anthropic_client=anthropic_client,
        context_builder=context_builder,
        tool_registry=tool_registry,
    )

    total_usage = TokenUsage()
    result: StepResult | None = None

    for _ in range(max_iterations):
        step = get_next_step(result, message)
        result, usage = step.execute(context)
        total_usage += usage

        context.trajectory.append(result)

        if is_truncated(result):
            raise ResponseTruncated()

        if is_done(result):
            return LoopOutcome(trajectory=context.trajectory, usage=total_usage)

    raise MaxIterationsExceeded()


def get_next_step(result: StepResult | None, message: str) -> LoopStep:
    if result is None:
        return ModelStep({"role": "user", "content": message})

    if isinstance(result, ToolResult):
        return ModelStep(result.tool_result_message)

    if result.stop_reason is StopReason.TOOL_USE:
        return ActionStep(result.tool_calls)

    raise ValueError("Unable to determine the next step.")


def is_done(result: StepResult) -> bool:
    return isinstance(result, ModelResult) and result.stop_reason is StopReason.END_TURN


def is_truncated(result: StepResult) -> bool:
    """Whether the model ran out of room mid-reply."""
    return (
        isinstance(result, ModelResult) and result.stop_reason is StopReason.MAX_TOKENS
    )
