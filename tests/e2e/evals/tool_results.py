"""Reading the tool_result blocks back out of a trajectory."""

from typing import Any, cast

from anthropic.types import ToolResultBlockParam

from src.chatbot.loop_result import ToolResult, Trajectory


def tool_result_blocks(trajectory: Trajectory) -> list[ToolResultBlockParam]:
    return [
        block
        for step_result in trajectory
        if isinstance(step_result, ToolResult)
        for block in cast(list[Any], step_result.tool_result_message["content"])
    ]
