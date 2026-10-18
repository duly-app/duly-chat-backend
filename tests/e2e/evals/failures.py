from src.chatbot.loop_result import LoopOutcome
from tests.e2e.evals.eval_case import EvalCase


def failures(case: EvalCase, outcome: LoopOutcome) -> list[str]:
    """The names of the outcomes a run did not meet."""
    unmet = [
        type(expected).__name__
        for expected in case.trajectory_outcomes
        if not expected.evaluate(outcome.trajectory)
    ]

    unmet += [
        type(expected).__name__
        for expected in case.answer_outcomes
        if not expected.evaluate(outcome.answer)
    ]

    return unmet
