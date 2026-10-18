from src.chatbot.loop_result import ModelResult, Trajectory
from src.chatbot.tools.tool import Tool
from tests.e2e.evals.outcome.outcome import Outcome
from tests.e2e.evals.tool_results import tool_result_blocks


class ToolResultMatch(Outcome[Trajectory]):
    """Something the tool returned satisfies the given outcome."""

    tool_class: type[Tool]
    outcome: Outcome[str]

    def __init__(self, tool_class: type[Tool], outcome: Outcome[str]):
        self.tool_class = tool_class
        self.outcome = outcome

    def evaluate(self, answer: Trajectory) -> bool:
        call_ids = {
            call.id
            for step_result in answer
            if isinstance(step_result, ModelResult)
            for call in step_result.tool_calls
            if call.name == self.tool_class.name
        }

        return any(
            self.outcome.evaluate(block["content"])
            for block in tool_result_blocks(answer)
            if block["tool_use_id"] in call_ids and isinstance(block["content"], str)
        )
