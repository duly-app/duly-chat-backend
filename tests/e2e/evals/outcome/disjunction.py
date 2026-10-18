from typing import Generic, Sequence

from tests.e2e.evals.outcome.outcome import AnswerT, Outcome


class AnyOf(Outcome[AnswerT], Generic[AnswerT]):
    """Met when at least one of the outcomes it holds is."""

    outcomes: Sequence[Outcome[AnswerT]]

    def __init__(self, outcomes: Sequence[Outcome[AnswerT]]):
        if not outcomes:
            raise ValueError("AnyOf needs at least one outcome")

        self.outcomes = outcomes

    def evaluate(self, answer: AnswerT) -> bool:
        return any(outcome.evaluate(answer) for outcome in self.outcomes)
