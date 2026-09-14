from uuid import UUID

from src.chatbot.tools.get_notes import GetNotes
from src.chatbot.tools.registry import create_tool_registry
from tests.integration.conftest import APIAdapterFactory
from tests.integration.fakes.fake_token_service import FakeTokenService

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
UNKNOWN_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
THREAD_ID = "thread-1"


def test_get_notes_renders_the_notes_of_the_token_user(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", "test-secret")
    token = FakeTokenService.create_fake_token(USER_ID)

    rendered = GetNotes(adapter, USER_ID, THREAD_ID, token).run()

    assert rendered.startswith("# Project ideas")
    assert "Build a chatbot for note-taking" in rendered
    # One heading per note.
    assert rendered.count("\n\n# ") == 4


def test_get_notes_says_so_when_there_are_none(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", "test-secret")
    token = FakeTokenService.create_fake_token(UNKNOWN_USER_ID)

    rendered = GetNotes(adapter, UNKNOWN_USER_ID, THREAD_ID, token).run()

    assert rendered == "The user has no notes."


def test_get_notes_ignores_arguments_it_does_not_declare(
    api_adapter: APIAdapterFactory,
):
    adapter = api_adapter("db_1", "test-secret")
    token = FakeTokenService.create_fake_token(USER_ID)

    # The model can send keys the schema does not mention; that must not crash.
    rendered = GetNotes(adapter, USER_ID, THREAD_ID, token).run(query="fastapi")

    assert rendered.startswith("# Project ideas")


def test_registry_creates_tool_with_curried_adapter(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1", "test-secret")
    registry = create_tool_registry(adapter)
    token = FakeTokenService.create_fake_token(USER_ID)

    registered = registry["get_notes"]
    rendered = registered.create(USER_ID, THREAD_ID, token).run()

    assert registered.schema["name"] == "get_notes"
    assert "# Project ideas" in rendered
