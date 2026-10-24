"""How a case answers the approval prompts its question provokes.

A gated write stops the turn, so without a policy every write case would
only ever assert that the assistant *asked*.
"""

from enum import StrEnum

from src.chatbot.approval import Decision, Decisions
from src.chatbot.loop_result import LoopOutcome


class Approvals(StrEnum):
    APPROVE = "approve"
    DECLINE = "decline"
    #: Leave the prompt unanswered, for a case about the gate itself.
    HOLD = "hold"


def decisions(outcome: LoopOutcome, policy: Approvals) -> Decisions:
    return {
        action.tool_use_id: Decision(approved=policy is Approvals.APPROVE)
        for action in outcome.pending
    }
