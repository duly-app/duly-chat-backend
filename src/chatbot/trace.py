import json
from typing import Any, Iterator, Mapping

from src.chatbot.loop_result import LoopOutcome, ModelResult, StepResult, ToolResult
from src.chatbot.threads.thread_store import ThreadID, TurnID
from src.domain.user import UserID
from src.logs import get_logger

TURN_EVENT = "turn"
STEP_EVENT = "step"
TURN_FAILED_EVENT = "turn_failed"
MAX_CONTENT = 500

logger = get_logger(__name__)


def log_step(
    turn_id: TurnID,
    user_id: UserID,
    thread_id: ThreadID,
    index: int,
    result: StepResult,
) -> None:
    logger.info(
        "step complete",
        extra={
            "event": STEP_EVENT,
            **_identity(turn_id, user_id, thread_id),
            "index": index,
            **_step_fields(result),
        },
    )


def log_turn(
    turn_id: TurnID,
    user_id: UserID,
    thread_id: ThreadID,
    prompt: str,
    outcome: LoopOutcome,
    seconds: float,
) -> None:
    logger.info(
        "turn complete",
        extra={
            "event": TURN_EVENT,
            **_identity(turn_id, user_id, thread_id),
            "seconds": round(seconds, 3),
            "tokens": outcome.usage.token_count,
            "steps": len(outcome.trajectory),
            "stop_reason": _stop_reason(outcome),
            "prompt": prompt,
            "answer": outcome.answer,
            "tools": tool_calls(outcome.trajectory),
        },
    )


def log_turn_failed(
    turn_id: TurnID,
    user_id: UserID,
    thread_id: ThreadID,
    prompt: str,
    error: BaseException,
    seconds: float,
) -> None:
    logger.error(
        "turn failed",
        exc_info=error,
        extra={
            "event": TURN_FAILED_EVENT,
            **_identity(turn_id, user_id, thread_id),
            "seconds": round(seconds, 3),
            "error_type": type(error).__name__,
            "prompt": prompt,
        },
    )


def tool_calls(trajectory: list[StepResult]) -> list[dict[str, Any]]:
    """Every tool the model asked for, in order, and whether it came back an error."""
    failed = _failures_by_id(trajectory)

    return [
        {
            "name": call.name,
            "input": _as_mapping(call.input),
            "error": failed.get(call.id, False),
        }
        for step in trajectory
        if isinstance(step, ModelResult)
        for call in step.tool_calls
    ]


def _step_fields(result: StepResult) -> dict[str, Any]:
    if isinstance(result, ModelResult):
        return {
            "kind": "model",
            "stop_reason": result.stop_reason.value,
            "text": result.text,  # The prose between tool calls
            "tools": [
                {
                    "id": call.id,
                    "name": call.name,
                    "input": _as_mapping(call.input),
                }
                for call in result.tool_calls
            ],
        }

    return {
        "kind": "tool",
        "results": [
            {
                "id": str(block["tool_use_id"]),
                "error": bool(block.get("is_error")),
                "content": _truncate(block.get("content")),
            }
            for block in _result_blocks(result)
        ],
    }


def _failures_by_id(trajectory: list[StepResult]) -> dict[str, bool]:
    """is_error for each tool_use_id, from the results sent back to the model."""
    return {
        str(block["tool_use_id"]): bool(block.get("is_error"))
        for step in trajectory
        if isinstance(step, ToolResult)
        for block in _result_blocks(step)
    }


def _result_blocks(step: ToolResult) -> Iterator[Mapping[str, Any]]:
    content = step.tool_result_message.get("content", [])

    if isinstance(content, str):
        return

    for raw in content:
        if not isinstance(raw, dict):
            continue

        block: Mapping[str, Any] = raw

        if block.get("type") == "tool_result":
            yield block


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _truncate(content: object) -> str:
    text = content if isinstance(content, str) else json.dumps(content, default=str)

    return text if len(text) <= MAX_CONTENT else f"{text[:MAX_CONTENT]}…"


def _identity(turn_id: TurnID, user_id: UserID, thread_id: ThreadID) -> dict[str, str]:
    return {
        "turn_id": str(turn_id),
        "user_id": str(user_id),
        "thread_id": str(thread_id),
    }


def _stop_reason(outcome: LoopOutcome) -> str | None:
    result = outcome.result

    return result.stop_reason.value if isinstance(result, ModelResult) else None
