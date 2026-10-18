from src.chatbot.loop_result import Trajectory
from tests.e2e.evals.outcome.outcome import Outcome
from tests.e2e.evals.tool_results import tool_result_blocks


class NoToolErrors(Outcome[Trajectory]):
    """No tool reported a failure."""

    def evaluate(self, answer: Trajectory) -> bool:
        return not any(block.get("is_error") for block in tool_result_blocks(answer))
