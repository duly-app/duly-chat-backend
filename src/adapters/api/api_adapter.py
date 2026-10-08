from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.adapters.security.token_service import AbstractTokenService
from src.domain import Note, UserID
from src.domain.notes import NoteID
from src.domain.user import Token

TokenServiceT = TypeVar("TokenServiceT", bound=AbstractTokenService)


class APIAdapter(ABC, Generic[TokenServiceT]):
    _token_service: TokenServiceT

    def __init__(self, token_service: TokenServiceT):
        self._token_service = token_service

    @abstractmethod
    def get_notes(self, token: Token) -> list[Note]:
        raise NotImplementedError

    @abstractmethod
    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        raise NotImplementedError

    @abstractmethod
    def create_note(self, token: Token, title: str, content: str) -> Note:
        raise NotImplementedError

    @abstractmethod
    def update_note(
        self,
        token: Token,
        note_id: NoteID,
        title: str | None = None,
        content: str | None = None,
    ) -> Note:
        """Change the title, the content, or both. Omitted fields are left alone."""
        raise NotImplementedError

    @abstractmethod
    def delete_note(self, token: Token, note_id: NoteID) -> None:
        raise NotImplementedError

    def get_user_id(self, token: Token) -> UserID:
        """Who the token belongs to, for adapters that must resolve it themselves."""
        return self._token_service.get_user_id_from_token(token)
