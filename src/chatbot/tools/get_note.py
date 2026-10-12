from typing import Any

import requests

from src.chatbot.tools.notes_tool import NotesTool, as_note_id
from src.chatbot.tools.rendering import render_note


class GetNote(NotesTool):
    name = "get_note"
    description = (
        "Read one of the user's notes in full, by the id shown in a list or "
        "search result."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "note_id": {
                "type": "string",
                "description": "The id of the note, as shown in a previous result.",
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
            return render_note(self._api.get_note(self.jwt, note_id))
        except requests.HTTPError:
            # A note the user doesn't own is indistinguishable from one that
            # doesn't exist, by design, so there is only one thing to say.
            return "No note with that id."
