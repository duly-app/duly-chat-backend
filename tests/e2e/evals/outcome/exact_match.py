from tests.e2e.evals.outcome.outcome import Outcome


class ExactMatch(Outcome[str]):
    """The whole string, character for character."""

    match: str

    def __init__(self, match: str):
        self.match = match

    def evaluate(self, answer: str) -> bool:
        return answer == self.match
