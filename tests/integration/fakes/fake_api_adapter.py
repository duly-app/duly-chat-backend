from src.adapters.api.api_adapter import APIAdapter
from src.domain.notes import Note
from src.domain.user import Token, UserID
from tests.integration.fakes.fake_token_service import FakeTokenService
from tests.integration.helpers.note_db import NoteDB


class FakeAPIAdapter(APIAdapter[FakeTokenService]):
    _note_db: NoteDB

    def __init__(self, token_service: FakeTokenService, note_db: NoteDB):
        self._note_db = note_db

        super().__init__(token_service)

    def _get_notes(self, user_id: UserID, token: Token) -> list[Note]:
        return self._note_db.get_notes_by_user(user_id)
