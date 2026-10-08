from uuid import UUID, uuid4

import pytest
import requests

from tests.integration.conftest import APIAdapterFactory
from tests.integration.fakes.fake_token_service import FakeTokenService

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
SECRET_KEY = "test-secret"


def test_api_adapter_returns_notes_for_token_user(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(USER_ID)

    notes = adapter.get_notes(token)

    assert len(notes) == 5
    assert notes[0].title == "Project ideas"


def test_api_adapter_returns_empty_for_nonexistent_user(api_adapter: APIAdapterFactory):
    nonexistent_user = UUID("00000000-0000-0000-0000-000000000000")

    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(nonexistent_user)

    notes = adapter.get_notes(token)

    assert notes == []


def test_api_adapter_creates_a_note_the_user_can_then_read(
    api_adapter: APIAdapterFactory,
):
    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(USER_ID)

    created = adapter.create_note(token, title="Shopping", content="Olives")

    assert created.title == "Shopping"
    assert created.content == "Olives"

    note = next(
        (note for note in adapter.get_notes(token) if note.title == "Shopping"), None
    )
    assert note is not None


def test_api_adapter_updates_only_the_field_it_is_given(
    api_adapter: APIAdapterFactory,
):
    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(USER_ID)

    created = adapter.create_note(token, title="Shopping", content="Olives")
    adapter.update_note(token, created.id, content="Olives, bread")

    note = next(
        (note for note in adapter.get_notes(token) if note.id == created.id), None
    )
    assert note is not None
    assert note.content == "Olives, bread"
    assert note.title == "Shopping"


def test_api_adapter_hides_a_deleted_note(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(USER_ID)

    created = adapter.create_note(token, title="Shopping", content="Olives")
    adapter.delete_note(token, created.id)

    # Soft deleted, so the record still exists — it just has to be invisible.
    assert created.id not in [note.id for note in adapter.get_notes(token)]

    with pytest.raises(requests.HTTPError):
        adapter.update_note(token, created.id, title="Shopping again")


def test_api_adapter_searches_titles_and_content(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", SECRET_KEY)
    token = FakeTokenService.create_fake_token(USER_ID)

    by_title = adapter.get_notes_by_keyword(token, "strategy")
    assert [note.title for note in by_title] == ["Testing strategy"]

    # "Depends()" appears in the body of that note and in no title.
    by_content = adapter.get_notes_by_keyword(token, "depends")
    assert [note.title for note in by_content] == ["FastAPI patterns"]

    # One hit by title, one by content — both are returned.
    by_either = adapter.get_notes_by_keyword(token, "fastapi")
    assert [note.title for note in by_either] == [
        "Meeting notes - Sept 13",
        "FastAPI patterns",
    ]

    assert adapter.get_notes_by_keyword(token, "kumquats") == []


def test_api_adapter_will_not_touch_another_users_note(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", SECRET_KEY)
    owner_token = FakeTokenService.create_fake_token(USER_ID)
    stranger_token = FakeTokenService.create_fake_token(uuid4())

    created = adapter.create_note(owner_token, title="Private", content="Secret")

    # Indistinguishable from a note that doesn't exist
    with pytest.raises(requests.HTTPError):
        adapter.update_note(stranger_token, created.id, title="Mine now")

    with pytest.raises(requests.HTTPError):
        adapter.delete_note(stranger_token, created.id)

    assert created.title == "Private"
    assert adapter.get_notes(stranger_token) == []
