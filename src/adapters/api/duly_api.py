import requests

from src.adapters.api.api_adapter import APIAdapter
from src.adapters.security.jwt_token_service import JWTTokenService
from src.domain import Note
from src.domain.user import Token, UserID


class DulyAPI(APIAdapter[JWTTokenService]):
    _service_uri: str

    def __init__(self, service_uri: str, token_service: JWTTokenService):
        self._service_uri = service_uri

        super().__init__(token_service)

    def _get_notes(self, user_id: UserID, token: Token) -> list[Note]:
        response = requests.get(
            f"{self._service_uri}/notes/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"user_id": str(user_id)},
        )
        response.raise_for_status()

        return [Note(**note_data) for note_data in response.json()]
