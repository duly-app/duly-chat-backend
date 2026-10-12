from typing import Any

import requests

from src.chatbot.tools.notes_tool import NotesTool, as_note_id


class DeleteNote(NotesTool):
    name = "delete_note"
    description = (
        "Delete one of the user's notes. Destructive: say which note you mean "
        "and get the user's explicit agreement before calling this."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "note_id": {
                "type": "string",
                "description": "The id of the note to delete.",
            }
        },
        "required": ["note_id"],
    }

    def run(self, **tool_input: Any) -> str:
        note_id = as_note_id(tool_input.get("note_id"))

        if note_id is None:
            return (
                "That is not a valid note id. Use an id from a list or search result."
            )

        try:
            self._api.delete_note(self.jwt, note_id)
        except requests.HTTPError:
            return "No note with that id."

        return "Deleted."
