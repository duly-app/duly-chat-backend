import datetime

import jwt

SERVICE_TOKEN_TYPE = "service"
SERVICE_TOKEN_HEADER = "X-Service-Token"
SERVICE_TOKEN_LIFETIME = datetime.timedelta(seconds=60)
SERVICE_SUBJECT = "duly-chat-backend"


class ServiceTokenService:
    """Mints the credential proving a write came from this service, not a user.

    Signed with a key shared only with the notes service, and deliberately not
    the key that signs user tokens: a leak of one must not reach the other."""

    _service_key: str

    def __init__(self, service_key: str):
        self._service_key = service_key

    def create_token(self) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)

        payload = {
            "sub": SERVICE_SUBJECT,
            "iat": now,
            "exp": now + SERVICE_TOKEN_LIFETIME,
            "type": SERVICE_TOKEN_TYPE,
        }

        return jwt.encode(payload, self._service_key, algorithm="HS256")
