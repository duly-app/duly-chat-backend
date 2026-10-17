from abc import ABC, abstractmethod
from datetime import datetime

from src.domain import Note
from src.domain.notes import NoteID
from src.domain.user import Token


class APIAdapter(ABC):
    @abstractmethod
    def get_notes(
        self,
        token: Token,
        order_by: str | None = None,
        descending: bool = True,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
    ) -> list[Note]:
        """A user's notes, newest first unless told otherwise.

        order_by is passed through as a string rather than mirroring the other
        service's enum: the allowed values are declared in the tool's schema,
        where they also constrain the model, and the API falls back on anything
        it doesn't recognise.
        """
        raise NotImplementedError

    @abstractmethod
    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        raise NotImplementedError

    @abstractmethod
    def get_note(self, token: Token, note_id: NoteID) -> Note:
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
