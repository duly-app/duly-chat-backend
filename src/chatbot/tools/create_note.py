from typing import Any

from src.chatbot.tools.notes_tool import NotesTool


class CreateNote(NotesTool):
    name = "create_note"
    description = "Create a new note for the user. Confirm the content with them first."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "A short title."},
            "content": {"type": "string", "description": "The body of the note."},
        },
        "required": ["title", "content"],
    }

    def run(self, **tool_input: Any) -> str:
        title = str(tool_input.get("title", "")).strip()

        if not title:
            return "A note needs a title."

        note = self._api.create_note(
            self.jwt, title=title, content=str(tool_input.get("content", ""))
        )

        return f'Created "{note.title}" (id: {note.id}).'
