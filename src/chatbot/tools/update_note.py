from typing import Any

import requests

from src.chatbot.tools.notes_tool import NotesTool, as_note_id


class UpdateNote(NotesTool):
    name = "update_note"
    description = (
        "Change a note's title, its content, or both. Whatever is left out is "
        "kept as it was, so send only what should change."
    )
    error_response = (
        "Could not reach the notes service. The note may or may not "
        "have been updated; check before trying again."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "note_id": {
                "type": "string",
                "description": "The id of the note to change.",
            },
            "title": {"type": "string", "description": "The new title."},
            "content": {"type": "string", "description": "The new body."},
        },
        "required": ["note_id"],
    }

    def run(self, **tool_input: Any) -> str:
        note_id = as_note_id(tool_input.get("note_id"))

        if note_id is None:
            return (
                "That is not a valid note id. Use an id from a list or search result."
            )

        title = tool_input.get("title")
        content = tool_input.get("content")

        if title is None and content is None:
            return "Nothing to change: give a new title, new content, or both."

        try:
            note = self._api.update_note(
                self.jwt,
                note_id,
                title=None if title is None else str(title),
                content=None if content is None else str(content),
            )
        except requests.HTTPError:
            return "No note with that id."

        return f'Updated "{note.title}" (id: {note.id}).'
