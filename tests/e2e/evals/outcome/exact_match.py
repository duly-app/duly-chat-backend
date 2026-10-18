from tests.e2e.evals.outcome.outcome import Outcome


class ExactMatch(Outcome[str]):
    """The whole string, character for character.

    For structured subjects: model prose varies too much to match exactly.
    """

    match: str

    def __init__(self, match: str):
        self.match = match

    def evaluate(self, answer: str) -> bool:
        return answer == self.match
