from datetime import datetime
from typing import Any

from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.rendering import as_limit, render_notes

ORDERS = ("last_updated", "created_at", "title")


class ListNotes(NotesTool):
    name = "list_notes"
    description = (
        "List the user's notes. Returns a preview of each note with its id; "
        "call get_note for a note's full text. Prefer search_notes when the "
        "user is asking about a particular subject."
    )
    error_response = (
        "Could not reach the notes service, so the notes could not be listed."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "How many notes to return at most. Defaults to 10.",
            },
            "order_by": {
                "type": "string",
                "enum": list(ORDERS),
                "description": (
                    "What to sort by. Defaults to last_updated, "
                    "which is most recently changed first."
                ),
            },
            "direction": {
                "type": "string",
                "enum": ["desc", "asc"],
                "description": "Sort direction. Defaults to desc.",
            },
            "updated_after": {
                "type": "string",
                "description": (
                    "Only notes changed at or after this ISO 8601 timestamp, "
                    "e.g. 2026-10-14T00:00:00. Call current_time first if you "
                    "need to work out what a date like 'yesterday' is."
                ),
            },
            "updated_before": {
                "type": "string",
                "description": (
                    "Only notes changed strictly before this ISO 8601 "
                    "timestamp. One whole day is updated_after at midnight "
                    "and updated_before at the next midnight."
                ),
            },
        },
    }

    def run(self, **tool_input: Any) -> str:
        notes = self._api.get_notes(
            self.jwt,
            order_by=_order(tool_input.get("order_by")),
            descending=tool_input.get("direction") != "asc",
            updated_after=_timestamp(tool_input.get("updated_after")),
            updated_before=_timestamp(tool_input.get("updated_before")),
        )

        return render_notes(notes, as_limit(tool_input.get("limit")))


def _order(value: object) -> str | None:
    """Drop anything outside the schema's enum rather than passing it on."""
    return value if value in ORDERS else None


def _timestamp(value: object) -> datetime | None:
    """Coerce a model-supplied timestamp, ignoring one it got wrong."""
    if not isinstance(value, str):
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
