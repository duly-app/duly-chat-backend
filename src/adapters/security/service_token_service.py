import datetime
from enum import StrEnum

from src.adapters.security import jwt_codec

SERVICE_TOKEN_HEADER = "X-Service-Token"
SERVICE_TOKEN_LIFETIME = datetime.timedelta(seconds=60)
SERVICE_SUBJECT = "duly-chat-backend"


class ServiceTokenType(StrEnum):
    SERVICE = "service"


class ServiceTokenService:
    """Mints the credential proving a write came from this service, not a user.

    Signed with a key shared only with the notes service.
    """

    _service_key: str

    def __init__(self, service_key: str):
        self._service_key = service_key

    def create_token(self) -> str:
        return jwt_codec.encode(
            SERVICE_SUBJECT,
            self._service_key,
            SERVICE_TOKEN_LIFETIME,
            ServiceTokenType.SERVICE,
        )
