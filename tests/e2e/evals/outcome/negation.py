from typing import Generic

from tests.e2e.evals.outcome.outcome import AnswerT, Outcome


class Not(Outcome[AnswerT], Generic[AnswerT]):
    """Met when the outcome it wraps is not."""

    outcome: Outcome[AnswerT]

    def __init__(self, outcome: Outcome[AnswerT]):
        self.outcome = outcome

    def evaluate(self, answer: AnswerT) -> bool:
        return not self.outcome.evaluate(answer)
