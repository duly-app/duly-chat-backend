"""Signing and verifying JWTs, with no opinion about what a token means."""

import datetime
from enum import StrEnum
from typing import Generic, TypedDict, TypeVar

import jwt

TokenTypeT = TypeVar("TokenTypeT", bound=StrEnum)


class TokenPayload(TypedDict, Generic[TokenTypeT]):
    sub: str
    iat: datetime.datetime
    exp: datetime.datetime
    type: TokenTypeT


def encode(
    subject: str,
    secret_key: str,
    lifetime: datetime.timedelta,
    token_type: StrEnum,
) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + lifetime,
        "type": token_type.value,
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode(
    token: str, secret_key: str, token_types: type[TokenTypeT]
) -> TokenPayload[TokenTypeT] | None:
    """The token's claims, or None if it is unusable for any reason.

    Unusable covers a bad signature, an expired token, a missing claim, and one
    declaring a type outside token_types.
    """
    try:
        decoding = jwt.decode(token, secret_key, algorithms=["HS256"])

        return {
            "sub": decoding["sub"],
            "iat": decoding["iat"],
            "exp": decoding["exp"],
            "type": token_types(decoding["type"]),
        }
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
