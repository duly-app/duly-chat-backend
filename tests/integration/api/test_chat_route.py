from datetime import timedelta
from enum import StrEnum
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from src.adapters.security import jwt_codec
from src.adapters.security.token_service import TokenService, TokenType
from src.app import create_app
from tests.integration.fakes.fake_env import FakeEnv

SIGNING_KEY = "signing-key-that-is-at-least-32-bytes-long"

THREAD_URL = "/threads/550e8400-e29b-41d4-a716-4466554400aa/messages"


class RefreshType(StrEnum):
    REFRESH = "refresh"


@pytest.fixture
def client():
    with TestClient(create_app(FakeEnv())) as test_client:
        yield test_client


def test_an_invalid_token_is_rejected_with_401(client: TestClient):
    response = client.post(
        THREAD_URL,
        json={"message": "hello"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_a_missing_token_is_rejected(client: TestClient):
    response = client.post(THREAD_URL, json={"message": "hello"})

    assert response.status_code == 401


def test_a_malformed_thread_id_is_rejected(client: TestClient):
    response = client.post(
        "/threads/not-a-uuid/messages",
        json={"message": "hello"},
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 422


def test_a_refresh_token_is_not_accepted_as_a_chat_credential():
    """A refresh token is for /api/refresh, and lives a week rather than 15 minutes."""
    user_id = UUID("550e8400-e29b-41d4-a716-446655440099")
    service = TokenService(SIGNING_KEY)

    access = jwt_codec.encode(
        str(user_id), SIGNING_KEY, timedelta(minutes=15), TokenType.ACCESS
    )
    refresh = jwt_codec.encode(
        str(user_id), SIGNING_KEY, timedelta(days=7), RefreshType.REFRESH
    )

    assert service.decode_token(access) is not None
    assert service.decode_token(refresh) is None
