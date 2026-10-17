"""Real user tokens for tests.

Minted with the same codec duly-backend uses.
"""

from datetime import timedelta
from enum import StrEnum

from src.adapters.security import jwt_codec
from src.adapters.security.token_service import TokenType
from src.domain.user import UserID

TEST_SIGNING_KEY = "signing-key-that-is-at-least-32-bytes-long"

ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)


class OtherTokenType(StrEnum):
    """A type this service does not accept, for the tests that prove it."""

    REFRESH = "refresh"


def access_token(
    user_id: UserID,
    secret_key: str = TEST_SIGNING_KEY,
    lifetime: timedelta = ACCESS_TOKEN_LIFETIME,
) -> str:
    return jwt_codec.encode(str(user_id), secret_key, lifetime, TokenType.ACCESS)


def refresh_token(user_id: UserID, secret_key: str = TEST_SIGNING_KEY) -> str:
    """What duly-backend puts in a cookie, which this service must refuse."""
    return jwt_codec.encode(
        str(user_id), secret_key, timedelta(days=7), OtherTokenType.REFRESH
    )
