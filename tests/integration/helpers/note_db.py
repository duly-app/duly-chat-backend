import datetime
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import UUID

from src.domain.notes import Note
from src.domain.user import UserID


@dataclass
class FullNote:
    """Full note with database fields (for testing only)."""

    id: UUID
    title: str
    content: str
    created_at: datetime.datetime
    user_id: UserID
    owner: UserID
    deleted: bool = False
    version: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "FullNote":
        data["created_at"] = datetime.datetime.fromisoformat(
            data["created_at"].replace("Z", "+00:00")
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
        )


class NoteDB:
    notes: list[FullNote]

    def __init__(self, note_db_path: Path):
        self.notes = list(self._parse_notes(note_db_path))

    def _parse_notes(self, path: Path) -> Iterable[FullNote]:
        with path.open("r") as f:
            notes_data = json.load(f)
            for note_dict in notes_data:
                yield FullNote.from_dict(note_dict)

    def get_notes_by_user(self, user_id: UserID) -> list[Note]:
        return [fn.to_note() for fn in self.notes if fn.user_id == user_id]
