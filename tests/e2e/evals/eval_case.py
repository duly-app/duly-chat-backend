from dataclasses import dataclass, field
from pathlib import Path

from src.chatbot.loop_result import Trajectory
from src.chatbot.tools.tool import Tool
from tests.e2e.evals.approvals import Approvals
from tests.e2e.evals.outcome.outcome import Outcome


@dataclass(frozen=True)
class EvalCase:
    """One question put to the assistant, and what should come back."""

    name: str
    question: str
    db: str
    trajectory_outcomes: list[Outcome[Trajectory]] = field(default_factory=list)
    answer_outcomes: list[Outcome[str]] = field(default_factory=list)
    available_tools: list[type[Tool]] | None = None
    approvals: Approvals = Approvals.APPROVE
    system_template: Path | None = None
