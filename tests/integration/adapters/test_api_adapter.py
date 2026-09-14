from uuid import UUID

from tests.integration.conftest import APIAdapterFactory
from tests.integration.fakes.fake_token_service import FakeTokenService


def test_api_adapter_returns_notes_for_token_user(api_adapter: APIAdapterFactory):
    user_id = UUID("550e8400-e29b-41d4-a716-446655440099")
    secret_key = "test-secret"

    adapter = api_adapter("db_1", secret_key)
    token = FakeTokenService.create_fake_token(user_id)

    notes = adapter.get_notes(token)

    assert len(notes) == 5
    assert notes[0].title == "Project ideas"


def test_api_adapter_returns_empty_for_nonexistent_user(api_adapter: APIAdapterFactory):
    nonexistent_user = UUID("00000000-0000-0000-0000-000000000000")
    secret_key = "test-secret"

    adapter = api_adapter("db_1", secret_key)
    token = FakeTokenService.create_fake_token(nonexistent_user)

    notes = adapter.get_notes(token)

    assert notes == []
