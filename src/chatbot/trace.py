from typing import Any, Mapping

from src.chatbot.loop_result import LoopOutcome, ModelResult, ToolResult, Trajectory
from src.chatbot.threads.thread_store import ThreadID
from src.domain.user import UserID
from src.logs import get_logger

TURN_EVENT = "turn"

logger = get_logger(__name__)


def log_turn(
    user_id: UserID,
    thread_id: ThreadID,
    prompt: str,
    outcome: LoopOutcome,
    seconds: float,
) -> None:
    """Record a finished turn: what was asked, what came back, what it cost."""
    logger.info(
        "turn complete",
        extra={
            "event": TURN_EVENT,
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "seconds": round(seconds, 3),
            "tokens": outcome.usage.token_count,
            "steps": len(outcome.trajectory),
            "stop_reason": _stop_reason(outcome),
            "prompt": prompt,
            "answer": outcome.answer,
            "tools": tool_calls(outcome.trajectory),
        },
    )


def tool_calls(trajectory: Trajectory) -> list[dict[str, Any]]:
    """Every tool the model asked for, in order, and whether it came back an error."""
    failed = _failures_by_id(trajectory)

    return [
        {
            "name": call.name,
            "input": call.input if isinstance(call.input, dict) else {},
            "error": failed.get(call.id, False),
        }
        for step in trajectory
        if isinstance(step, ModelResult)
        for call in step.tool_calls
    ]


def _failures_by_id(trajectory: Trajectory) -> dict[str, bool]:
    """is_error for each tool_use_id, from the results sent back to the model."""
    failures: dict[str, bool] = {}

    for step in trajectory:
        if not isinstance(step, ToolResult):
            continue

        content = step.tool_result_message.get("content", [])

        if isinstance(content, str):
            continue

        for raw in content:
            if not isinstance(raw, dict):
                continue

            block: Mapping[str, Any] = raw

            if block.get("type") == "tool_result":
                failures[str(block["tool_use_id"])] = bool(block.get("is_error"))

    return failures


def _stop_reason(outcome: LoopOutcome) -> str | None:
    result = outcome.result

    return result.stop_reason.value if isinstance(result, ModelResult) else None
