from typing import Type

from src.chatbot.loop_result import ApprovalRequired, Trajectory
from src.chatbot.tools.tool import Tool
from tests.e2e.evals.outcome.outcome import Outcome


class AwaitsApproval(Outcome[Trajectory]):
    """The run stopped to ask the user about this tool, rather than running it."""

    tool_class: Type[Tool]

    def __init__(self, tool_class: Type[Tool]):
        self.tool_class = tool_class

    def evaluate(self, answer: Trajectory) -> bool:
        return any(
            action.name == self.tool_class.name
            for step in answer
            if isinstance(step, ApprovalRequired)
            for action in step.pending
        )
