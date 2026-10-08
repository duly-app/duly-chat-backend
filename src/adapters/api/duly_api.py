from datetime import datetime
from typing import Any
from uuid import UUID

import requests

from src.adapters.api.api_adapter import APIAdapter
from src.adapters.security.jwt_token_service import JWTTokenService
from src.domain import Note
from src.domain.notes import NoteID
from src.domain.user import Token


class DulyAPI(APIAdapter[JWTTokenService]):
    _service_uri: str

    def __init__(self, service_uri: str, token_service: JWTTokenService):
        self._service_uri = service_uri

        super().__init__(token_service)

    def get_notes(self, token: Token) -> list[Note]:
        response = requests.get(
            f"{self._service_uri}/notes", headers=self._headers(token)
        )
        response.raise_for_status()

        return [self._to_note(note_data) for note_data in response.json()]

    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        response = requests.get(
            f"{self._service_uri}/notes/search",
            headers=self._headers(token),
            params={"keyword": keyword},
        )
        response.raise_for_status()

        return [self._to_note(note_data) for note_data in response.json()]

    def create_note(self, token: Token, title: str, content: str) -> Note:
        response = requests.post(
            f"{self._service_uri}/notes",
            headers=self._headers(token),
            json={"title": title, "content": content},
        )
        response.raise_for_status()

        return self._to_note(response.json())

    def update_note(
        self,
        token: Token,
        note_id: NoteID,
        title: str | None = None,
        content: str | None = None,
    ) -> Note:
        changes = {
            field: value
            for field, value in (("title", title), ("content", content))
            if value is not None
        }

        response = requests.put(
            f"{self._service_uri}/notes/{note_id}",
            headers=self._headers(token),
            json=changes,
        )
        response.raise_for_status()

        return self._to_note(response.json())

    def delete_note(self, token: Token, note_id: NoteID) -> None:
        response = requests.delete(
            f"{self._service_uri}/notes/{note_id}", headers=self._headers(token)
        )
        response.raise_for_status()

    @staticmethod
    def _headers(token: Token) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _to_note(data: dict[str, Any]) -> Note:
        """Narrow a serialized note down to what this service models.

        The API also sends last_updated and last_author_type, and sends the id
        and timestamps as strings, so the fields can't be splatted straight in.
        """
        return Note(
            id=UUID(data["id"]),
            title=data["title"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
