"""Reading the user tokens duly-backend issues, signed with SIGNING_KEY.

Read-only: this service never mints a user token, it only decides whether the
one it was handed is usable.
"""

from enum import StrEnum
from typing import TypeAlias
from uuid import UUID

from src.adapters.security import jwt_codec
from src.adapters.security.jwt_codec import TokenPayload
from src.domain.user import UserID


class TokenType(StrEnum):
    ACCESS = "access"


UserTokenPayload: TypeAlias = TokenPayload[TokenType]


class TokenService:
    _secret_key: str

    def __init__(self, secret_key: str):
        self._secret_key = secret_key

    def decode_token(self, token: str) -> UserTokenPayload | None:
        return jwt_codec.decode(token, self._secret_key, TokenType)

    @staticmethod
    def get_token_from_header(authorization_header: str | None) -> str | None:
        if not authorization_header:
            return None

        if not authorization_header.startswith("Bearer "):
            return None

        return authorization_header.replace("Bearer ", "", count=1)

    @property
    def secret_key(self) -> str:
        return self._secret_key

    def get_user_id_from_token(self, token: str) -> UserID:
        payload = self.decode_token(token)

        if not payload:
            raise ValueError("Invalid or expired token")

        return UUID(payload["sub"])
