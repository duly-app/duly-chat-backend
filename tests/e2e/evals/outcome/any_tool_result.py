from src.chatbot.loop_result import Trajectory
from tests.e2e.evals.outcome.outcome import Outcome
from tests.e2e.evals.tool_results import tool_result_blocks


class AnyToolResult(Outcome[Trajectory]):
    """Something a tool returned satisfies the given outcome, whichever tool."""

    outcome: Outcome[str]

    def __init__(self, outcome: Outcome[str]):
        self.outcome = outcome

    def evaluate(self, answer: Trajectory) -> bool:
        return any(
            self.outcome.evaluate(block["content"])
            for block in tool_result_blocks(answer)
            if isinstance(block["content"], str)
        )
