from abc import ABC, abstractmethod
from typing import Generic, TypeVar

AnswerT = TypeVar("AnswerT")


class Outcome(ABC, Generic[AnswerT]):
    @abstractmethod
    def evaluate(self, answer: AnswerT) -> bool:
        raise NotImplementedError()
