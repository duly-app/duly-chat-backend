from typing import Generic, Sequence

from tests.e2e.evals.outcome.outcome import AnswerT, Outcome


class AllOf(Outcome[AnswerT], Generic[AnswerT]):
    """Met when every outcome it holds is."""

    outcomes: Sequence[Outcome[AnswerT]]

    def __init__(self, outcomes: Sequence[Outcome[AnswerT]]):
        if not outcomes:
            raise ValueError("AllOf needs at least one outcome")

        self.outcomes = outcomes

    def evaluate(self, answer: AnswerT) -> bool:
        return all(outcome.evaluate(answer) for outcome in self.outcomes)
