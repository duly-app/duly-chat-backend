from tests.e2e.evals.outcome.outcome import Outcome


class KeywordMatch(Outcome[str]):
    """Every keyword appears, ignoring case."""

    keywords: list[str]

    def __init__(self, keywords: list[str]):
        if not keywords:
            raise ValueError("KeywordMatch needs at least one keyword")

        self.keywords = keywords

    def evaluate(self, answer: str) -> bool:
        haystack = answer.lower()

        return all(keyword.lower() in haystack for keyword in self.keywords)
