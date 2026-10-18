import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4

import requests

from src.domain.notes import Note
from src.domain.user import UserID


@dataclass
class FullNote:
    """Full note with database fields (for testing only)."""

    id: UUID
    title: str
    content: str
    created_at: datetime.datetime
    last_updated: datetime.datetime
    user_id: UserID
    owner: UserID
    deleted: bool = False
    version: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "FullNote":
        for field in ("created_at", "last_updated"):
            data[field] = datetime.datetime.fromisoformat(
                data[field].replace("Z", "+00:00")
            )

        data["user_id"] = UUID(data["user_id"])
        data["owner"] = UUID(data["owner"])
        data["id"] = UUID(data["id"])

        return cls(**data)

    def to_note(self) -> Note:
        return Note(
            id=self.id,
            title=self.title,
            content=self.content,
            created_at=self.created_at,
            last_updated=self.last_updated,
        )


def _utc(value: datetime.datetime | None) -> datetime.datetime | None:
    """Read a naive bound as UTC, as a timestamptz column would.

    The notes carry offsets, so comparing them against a naive bound raises.
    """
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=datetime.timezone.utc)


class NoteDB:
    notes: list[FullNote]

    def __init__(self, note_db_path: Path):
        self.notes = list(self._parse_notes(note_db_path))

    def _parse_notes(self, path: Path) -> Iterable[FullNote]:
        with path.open("r") as f:
            notes_data = json.load(f)
            for note_dict in notes_data:
                yield FullNote.from_dict(note_dict)

    def get_notes_by_user(
        self,
        user_id: UserID,
        order_by: str = "last_updated",
        descending: bool = True,
        updated_after: datetime.datetime | None = None,
        updated_before: datetime.datetime | None = None,
    ) -> list[Note]:
        after = _utc(updated_after)
        before = _utc(updated_before)

        def in_window(note: Note) -> bool:
            if after is not None and note.last_updated < after:
                return False

            return before is None or note.last_updated < before

        notes = [fn.to_note() for fn in self._live_notes(user_id)]

        return sorted(
            (note for note in notes if in_window(note)),
            key=lambda note: (getattr(note, order_by), str(note.id)),
            reverse=descending,
        )

    def search(self, user_id: UserID, keyword: str) -> list[Note]:
        """Case-insensitive substring match.

        The real service uses a tsvector, which stems words and won't match on
        a prefix, so this fake is more generous than production.
        """
        needle = keyword.lower()

        return [
            fn.to_note()
            for fn in self._live_notes(user_id)
            if needle in fn.title.lower() or needle in fn.content.lower()
        ]

    def get(self, user_id: UserID, note_id: UUID) -> Note:
        return self._owned_note(user_id, note_id).to_note()

    def add(self, user_id: UserID, title: str, content: str) -> Note:
        now = datetime.datetime.now(datetime.timezone.utc)
        note = FullNote(
            id=uuid4(),
            title=title,
            content=content,
            created_at=now,
            last_updated=now,
            user_id=user_id,
            owner=user_id,
        )
        self.notes.append(note)

        return note.to_note()

    def update(
        self,
        user_id: UserID,
        note_id: UUID,
        title: str | None = None,
        content: str | None = None,
    ) -> Note:
        note = self._owned_note(user_id, note_id)

        if title is not None:
            note.title = title

        if content is not None:
            note.content = content

        note.last_updated = datetime.datetime.now(datetime.timezone.utc)
        note.version += 1

        return note.to_note()

    def delete(self, user_id: UserID, note_id: UUID) -> None:
        """Soft delete, as the real service does: the row is kept and flagged."""
        self._owned_note(user_id, note_id).deleted = True

    def _live_notes(self, user_id: UserID) -> Iterable[FullNote]:
        return [fn for fn in self.notes if fn.user_id == user_id and not fn.deleted]

    def _owned_note(self, user_id: UserID, note_id: UUID) -> FullNote:
        note = next((fn for fn in self._live_notes(user_id) if fn.id == note_id), None)

        if note is None:
            raise requests.HTTPError(f"404 Not Found: /notes/{note_id}")

        return note
