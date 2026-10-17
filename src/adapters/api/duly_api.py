from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.adapters.api.api_adapter import APIAdapter
from src.adapters.security.service_token_service import (
    SERVICE_TOKEN_HEADER,
    ServiceTokenService,
)
from src.domain import Note
from src.domain.notes import NoteID
from src.domain.user import Token


class HTTPResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


class HTTPClient(Protocol):

    def get(self, url: str, **kwargs: Any) -> HTTPResponse: ...

    def post(self, url: str, **kwargs: Any) -> HTTPResponse: ...

    def put(self, url: str, **kwargs: Any) -> HTTPResponse: ...

    def delete(self, url: str, **kwargs: Any) -> HTTPResponse: ...


class DulyAPI(APIAdapter):
    _service_uri: str
    _service_token_service: ServiceTokenService
    _http: HTTPClient

    def __init__(
        self,
        service_uri: str,
        service_token_service: ServiceTokenService,
        http_client: HTTPClient,
    ):
        self._service_uri = service_uri
        self._service_token_service = service_token_service
        self._http = http_client

    def get_notes(
        self,
        token: Token,
        order_by: str | None = None,
        descending: bool = True,
        updated_after: datetime | None = None,
        updated_before: datetime | None = None,
    ) -> list[Note]:
        params: dict[str, str] = {"direction": "desc" if descending else "asc"}

        if order_by:
            params["order_by"] = order_by

        if updated_after:
            params["updated_after"] = updated_after.isoformat()

        if updated_before:
            params["updated_before"] = updated_before.isoformat()

        response = self._http.get(
            f"{self._service_uri}/notes",
            headers=self._headers(token),
            params=params,
        )
        response.raise_for_status()

        return [self._to_note(note_data) for note_data in response.json()["notes"]]

    def get_notes_by_keyword(self, token: Token, keyword: str) -> list[Note]:
        response = self._http.get(
            f"{self._service_uri}/notes/search",
            headers=self._headers(token),
            params={"keyword": keyword},
        )
        response.raise_for_status()

        return [self._to_note(note_data) for note_data in response.json()["notes"]]

    def get_note(self, token: Token, note_id: NoteID) -> Note:
        response = self._http.get(
            f"{self._service_uri}/notes/{note_id}", headers=self._headers(token)
        )
        response.raise_for_status()

        return self._to_note(response.json())

    def create_note(self, token: Token, title: str, content: str) -> Note:
        response = self._http.post(
            f"{self._service_uri}/notes",
            headers=self._write_headers(token),
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

        response = self._http.put(
            f"{self._service_uri}/notes/{note_id}",
            headers=self._write_headers(token),
            json=changes,
        )
        response.raise_for_status()

        return self._to_note(response.json())

    def delete_note(self, token: Token, note_id: NoteID) -> None:
        response = self._http.delete(
            f"{self._service_uri}/notes/{note_id}",
            headers=self._write_headers(token),
        )
        response.raise_for_status()

    @staticmethod
    def _headers(token: Token) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _write_headers(self, token: Token) -> dict[str, str]:
        return {
            **self._headers(token),
            SERVICE_TOKEN_HEADER: self._service_token_service.create_token(),
        }

    @staticmethod
    def _to_note(data: dict[str, Any]) -> Note:
        """Narrow a serialized note down to what this service models."""
        return Note(
            id=UUID(data["id"]),
            title=data["title"],
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"]),
        )
