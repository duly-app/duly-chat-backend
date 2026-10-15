from dataclasses import dataclass
from datetime import datetime
from typing import TypeAlias
from uuid import UUID

NoteID: TypeAlias = UUID


@dataclass
class Note:
    id: NoteID
    title: str
    content: str
    created_at: datetime
    last_updated: datetime
