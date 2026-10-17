from uuid import UUID

from tests.conftest import NoteDBFactory


def test_note_db_loads_notes(note_db: NoteDBFactory):
    db = note_db("db_1")

    assert len(db.notes) == 5
    assert db.notes[0].title == "Project ideas"


def test_note_db_filters_by_user(note_db: NoteDBFactory):
    db = note_db("db_1")
    user_id = UUID("550e8400-e29b-41d4-a716-446655440099")

    notes = db.get_notes_by_user(user_id)

    assert len(notes) == 5
    assert all(n.title for n in notes)


def test_note_db_returns_empty_for_nonexistent_user(note_db: NoteDBFactory):
    db = note_db("db_1")
    nonexistent_user = UUID("00000000-0000-0000-0000-000000000000")

    notes = db.get_notes_by_user(nonexistent_user)
    assert notes == []
