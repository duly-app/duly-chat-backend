from uuid import UUID, uuid4

from src.chatbot.tools.create_note import CreateNote
from src.chatbot.tools.current_time import CurrentTime
from src.chatbot.tools.delete_note import DeleteNote
from src.chatbot.tools.get_note import GetNote
from src.chatbot.tools.list_notes import ListNotes
from src.chatbot.tools.registry import NOTES_TOOLS, create_tool_registry
from src.chatbot.tools.search_notes import SearchNotes
from src.chatbot.tools.update_note import UpdateNote
from tests.integration.conftest import APIAdapterFactory
from tests.integration.helpers.tokens import access_token

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
UNKNOWN_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
THREAD_ID = UUID("550e8400-e29b-41d4-a716-4466554400aa")


def tool(tool_class, adapter, user_id=USER_ID):
    return tool_class(adapter, user_id, THREAD_ID, access_token(user_id))


def test_list_notes_previews_each_note_with_its_id(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    rendered = tool(ListNotes, adapter).run()

    assert rendered.startswith("5 notes.")

    # Ids have to be visible, or the model cannot name a note to any other tool.
    notes = adapter.get_notes(access_token(USER_ID))
    for note in notes:
        assert f"(id: {note.id}," in rendered


def test_list_notes_caps_its_output_and_says_it_did(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    rendered = tool(ListNotes, adapter).run(limit=2)

    # The count tells the model it is seeing a subset, so it can search instead
    # of assuming these are all the notes there are.
    assert rendered.startswith("Showing 2 of 5 notes.")
    assert rendered.count("(id: ") == 2


def test_list_notes_survives_a_nonsense_limit(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    # Models send strings, and occasionally rubbish. Neither may crash a turn.
    assert tool(ListNotes, adapter).run(limit="2").startswith("Showing 2 of 5")
    assert tool(ListNotes, adapter).run(limit="lots").startswith("5 notes.")
    assert tool(ListNotes, adapter).run(limit=-4).startswith("Showing 1 of 5")


def test_list_notes_says_so_when_there_are_none(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    assert tool(ListNotes, adapter, UNKNOWN_USER_ID).run() == "No notes found."


def test_search_notes_matches_titles_and_content(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    rendered = tool(SearchNotes, adapter).run(query="depends")

    assert rendered.startswith("1 note.")
    assert "# FastAPI patterns" in rendered


def test_search_notes_reports_a_miss_rather_than_guessing(
    api_adapter: APIAdapterFactory,
):
    adapter = api_adapter("db_1")

    assert tool(SearchNotes, adapter).run(query="kumquats") == "No notes found."
    assert "No query given" in tool(SearchNotes, adapter).run(query="  ")


def test_get_note_returns_the_whole_note(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_2")
    token = access_token(USER_ID)
    groceries = next(
        note for note in adapter.get_notes(token) if note.title == "Groceries"
    )

    rendered = tool(GetNote, adapter).run(note_id=str(groceries.id))

    # Previews truncate; this is the tool that does not.
    updated = groceries.last_updated.date().isoformat()

    assert rendered == (
        f"# Groceries (id: {groceries.id}, updated: {updated})\n{groceries.content}"
    )


def test_get_note_handles_an_id_the_model_invented(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    assert tool(GetNote, adapter).run(note_id=str(uuid4())) == "No note with that id."
    assert "not a valid note id" in tool(GetNote, adapter).run(note_id="the first one")


def test_create_note_reports_the_id_it_made(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    rendered = tool(CreateNote, adapter).run(title="Shopping", content="Olives")

    assert rendered.startswith('Created "Shopping" (id: ')

    # And it really is the user's now.
    assert "# Shopping" in tool(ListNotes, adapter).run(limit=50)


def test_create_note_refuses_an_empty_title(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")

    assert tool(CreateNote, adapter).run(content="Olives") == "A note needs a title."


def test_update_note_changes_only_what_it_is_given(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")
    token = access_token(USER_ID)
    created = adapter.create_note(token, title="Shopping", content="Olives")

    rendered = tool(UpdateNote, adapter).run(
        note_id=str(created.id), content="Olives, bread"
    )

    assert rendered == f'Updated "Shopping" (id: {created.id}).'
    assert adapter.get_note(token, created.id).title == "Shopping"


def test_update_note_needs_something_to_change(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")
    token = access_token(USER_ID)
    created = adapter.create_note(token, title="Shopping", content="Olives")

    rendered = tool(UpdateNote, adapter).run(note_id=str(created.id))

    assert "Nothing to change" in rendered


def test_delete_note_soft_deletes_it_out_of_sight(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")
    token = access_token(USER_ID)
    created = adapter.create_note(token, title="Shopping", content="Olives")

    assert tool(DeleteNote, adapter).run(note_id=str(created.id)) == "Deleted."
    assert "# Shopping" not in tool(ListNotes, adapter).run(limit=50)

    # Gone for a second attempt too, rather than reported as deleted twice.
    assert tool(DeleteNote, adapter).run(note_id=str(created.id)) == (
        "No note with that id."
    )


def test_a_tool_will_not_touch_another_users_note(api_adapter: APIAdapterFactory):
    adapter = api_adapter("db_1")
    owner_token = access_token(USER_ID)
    created = adapter.create_note(owner_token, title="Private", content="Secret")

    stranger = uuid4()

    # The token is the only identity a tool has, so it cannot reach across.
    assert tool(GetNote, adapter, stranger).run(note_id=str(created.id)) == (
        "No note with that id."
    )
    assert tool(DeleteNote, adapter, stranger).run(note_id=str(created.id)) == (
        "No note with that id."
    )
    assert adapter.get_note(owner_token, created.id).title == "Private"


def test_the_registry_exposes_every_tool_with_a_usable_schema(
    api_adapter: APIAdapterFactory,
):
    registry = create_tool_registry(api_adapter("db_1"))

    assert set(registry) == {tool_class.name for tool_class in NOTES_TOOLS} | {
        CurrentTime.name
    }

    for name, registered in registry.items():
        assert registered.schema["name"] == name
        assert registered.schema["description"]
        assert registered.schema["input_schema"]["type"] == "object"


def test_every_tool_declares_what_its_failure_means():
    for tool_class in NOTES_TOOLS:
        assert tool_class.error_response

    # The write tools must not claim the write definitely didn't happen: a
    # failure after the request was sent may still have landed.
    for tool_class in (CreateNote, UpdateNote, DeleteNote):
        assert "may or may not" in tool_class.error_response
