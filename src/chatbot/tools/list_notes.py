from typing import Any

from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.rendering import as_limit, render_notes


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
            }
        },
    }

    def run(self, **tool_input: Any) -> str:
        notes = self._api.get_notes(self.jwt)

        return render_notes(notes, as_limit(tool_input.get("limit")))
