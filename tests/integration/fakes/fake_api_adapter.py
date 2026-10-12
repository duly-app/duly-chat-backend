from src.adapters.api.api_adapter import APIAdapter
from src.domain.notes import Note, NoteID
from src.domain.user import Token
from tests.integration.fakes.fake_token_service import FakeTokenService
from tests.integration.helpers.note_db import NoteDB


class FakeAPIAdapter(APIAdapter[FakeTokenService]):
    """Stands in for the notes service, resolving the user from the token itself."""

    _note_db: NoteDB

    def __init__(self, token_service: FakeTokenService, note_db: NoteDB):
        self._note_db = note_db

        super().__init__(token_service)

    def get_notes(self, token: Token) -> list[Note]:
        return self._note_db.get_notes_by_user(self.get_user_id(token))

    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        return self._note_db.search(self.get_user_id(token), keyword)

    def get_note(self, token: Token, note_id: NoteID) -> Note:
        return self._note_db.get(self.get_user_id(token), note_id)

    def create_note(self, token: Token, title: str, content: str) -> Note:
        return self._note_db.add(self.get_user_id(token), title, content)

    def update_note(
        self,
        token: Token,
        note_id: NoteID,
        title: str | None = None,
        content: str | None = None,
    ) -> Note:
        return self._note_db.update(self.get_user_id(token), note_id, title, content)

    def delete_note(self, token: Token, note_id: NoteID) -> None:
        self._note_db.delete(self.get_user_id(token), note_id)
