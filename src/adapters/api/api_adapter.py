from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.adapters.security.token_service import AbstractTokenService
from src.domain import Note, UserID
from src.domain.user import Token

TokenServiceT = TypeVar("TokenServiceT", bound=AbstractTokenService)


class APIAdapter(ABC, Generic[TokenServiceT]):
    _token_service: TokenServiceT

    def __init__(self, token_service: TokenServiceT):
        self._token_service = token_service

    def get_notes(self, token: Token) -> list[Note]:
        user_id = self.get_user_id(token, self._token_service)

        return self._get_notes(user_id, token)

    @abstractmethod
    def _get_notes(self, user_id: UserID, token: Token) -> list[Note]:
        raise NotImplementedError

    @classmethod
    def get_user_id(cls, token: Token, token_service: TokenServiceT) -> UserID:
        return token_service.get_user_id_from_token(token)
