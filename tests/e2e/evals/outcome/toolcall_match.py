from typing import Dict, Type, TypeGuard

from src.chatbot.loop_result import ModelResult, StopReason, Trajectory
from src.chatbot.tools.tool import Tool
from tests.e2e.evals.outcome.outcome import Outcome


class ToolCallMatch(Outcome[Trajectory]):
    tool_class: Type[Tool]
    tool_input: Dict[str, object]

    def __init__(self, tool_class: Type[Tool], tool_input: Dict[str, object]):
        self.tool_class = tool_class
        self.tool_input = tool_input

    def evaluate(self, answer: Trajectory) -> bool:
        def calls_tool(step_result) -> TypeGuard[ModelResult]:
            return (
                isinstance(step_result, ModelResult)
                and step_result.stop_reason == StopReason.TOOL_USE
            )

        tool_call = next(
            (
                tool_call
                for step_result in answer
                if calls_tool(step_result)
                for tool_call in step_result.tool_calls
                if tool_call.name == self.tool_class.name
                and self.tool_input.items() <= tool_call.input.items()
            ),
            None,
        )

        return tool_call is not None
