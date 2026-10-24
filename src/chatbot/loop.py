from anthropic.types import ToolUseBlock

from src.chatbot.approval import Decisions
from src.chatbot.errors import MaxIterationsExceeded, ResponseTruncated
from src.chatbot.loop_result import (
    LoopOutcome,
    ModelResult,
    StepResult,
    StopReason,
    TokenUsage,
    ToolResult,
    is_awaiting_approval,
)
from src.chatbot.loop_step import ActionStep, LoopContext, LoopStep, ModelStep
from src.chatbot.trace import log_step

MAX_ITERATIONS = 10


def chat_loop(
    context: LoopContext, message: str, max_iterations: int = MAX_ITERATIONS
) -> LoopOutcome:
    """Answer a user's message, running whatever tools that takes."""
    return run_loop(
        context, ModelStep({"role": "user", "content": message}), max_iterations
    )


def resume_turn(
    context: LoopContext,
    tool_calls: list[ToolUseBlock],
    decisions: Decisions,
    max_iterations: int = MAX_ITERATIONS,
) -> LoopOutcome:
    """Carry on a turn that stopped for approval.

    The same loop as chat_loop: only the first step differs, running the tools
    the model already asked for instead of sending a new message.
    """
    return run_loop(context, ActionStep(tool_calls, decisions), max_iterations)


def run_loop(
    context: LoopContext,
    first_step: LoopStep,
    max_iterations: int = MAX_ITERATIONS,
) -> LoopOutcome:
    total_usage = TokenUsage()
    step = first_step

    for index in range(max_iterations):
        result, usage = step.execute(context)
        total_usage += usage

        context.trajectory.append(result)
        log_step(context.turn_id, context.user_id, context.thread_id, index, result)

        if is_truncated(result):
            raise ResponseTruncated()

        if is_finished(result):
            return LoopOutcome(trajectory=context.trajectory, usage=total_usage)

        next_step = get_next_step(result)

        if next_step is None:
            raise ValueError(
                f"Unable to determine the step after {type(result).__name__}"
            )

        step = next_step

    raise MaxIterationsExceeded()


def get_next_step(result: StepResult) -> LoopStep | None:
    if isinstance(result, ToolResult):
        return ModelStep(result.tool_result_message)

    if isinstance(result, ModelResult) and result.stop_reason is StopReason.TOOL_USE:
        return ActionStep(result.tool_calls)

    return None


def is_finished(result: StepResult) -> bool:
    """Whether the run is over, either answered or handed back to the user."""
    return is_answered(result) or is_awaiting_approval(result)


def is_answered(result: StepResult) -> bool:
    """Whether the model said its last word."""
    return isinstance(result, ModelResult) and result.stop_reason is StopReason.END_TURN


def is_truncated(result: StepResult) -> bool:
    """Whether the model ran out of room mid-reply."""
    return (
        isinstance(result, ModelResult) and result.stop_reason is StopReason.MAX_TOKENS
    )
