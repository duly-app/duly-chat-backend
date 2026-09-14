import datetime
from abc import ABC, abstractmethod
from typing import TypedDict
from uuid import UUID

from src.domain.user import UserID


class TokenPayload(TypedDict):
    sub: str
    iat: datetime.datetime
    exp: datetime.datetime


class AbstractTokenService(ABC):
    _secret_key: str

    def __init__(self, secret_key: str):
        self._secret_key = secret_key

    @abstractmethod
    def decode_token(self, token: str) -> TokenPayload | None:
        pass

    @classmethod
    def get_token_from_header(cls, authorization_header: str | None) -> str | None:
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
