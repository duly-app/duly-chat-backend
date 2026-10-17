from datetime import datetime

from src.adapters.api.api_adapter import APIAdapter
from src.adapters.security.token_service import TokenService
from src.domain.notes import Note, NoteID
from src.domain.user import Token, UserID
from tests.integration.helpers.note_db import NoteDB
from tests.integration.helpers.tokens import TEST_SIGNING_KEY


class FakeAPIAdapter(APIAdapter):
    """Stand-in for the notes service."""

    _note_db: NoteDB
    _token_service: TokenService

    def __init__(self, note_db: NoteDB, secret_key: str = TEST_SIGNING_KEY):
        self._note_db = note_db
        self._token_service = TokenService(secret_key)

    def get_notes(
        self,
        token: Token,
        order_by: str | None = None,
        descending: bool = True,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
    ) -> list[Note]:
        return self._note_db.get_notes_by_user(
            self._user_id(token),
            order_by=order_by or "last_updated",
            descending=descending,
            updated_after=updated_after,
            updated_before=updated_before,
        )

    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        return self._note_db.search(self._user_id(token), keyword)

    def get_note(self, token: Token, note_id: NoteID) -> Note:
        return self._note_db.get(self._user_id(token), note_id)

    def create_note(self, token: Token, title: str, content: str) -> Note:
        return self._note_db.add(self._user_id(token), title, content)

    def update_note(
        self,
        token: Token,
        note_id: NoteID,
        title: str | None = None,
        content: str | None = None,
    ) -> Note:
        return self._note_db.update(self._user_id(token), note_id, title, content)

    def delete_note(self, token: Token, note_id: NoteID) -> None:
        self._note_db.delete(self._user_id(token), note_id)

    def _user_id(self, token: Token) -> UserID:
        return self._token_service.get_user_id_from_token(token)
