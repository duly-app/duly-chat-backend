from typing import Any

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.threads.thread_store import ThreadID
from src.chatbot.tools.tool import Tool
from src.domain.notes import Note
from src.domain.user import Token, UserID


class GetNotes(Tool):
    name = "get_notes"
    description = "Retrieve the notes belonging to the current user."
    input_schema = {"type": "object", "properties": {}}

    def __init__(
        self,
        api_adapter: APIAdapter,
        user_id: UserID,
        thread_id: ThreadID,
        jwt: Token,
    ):
        super().__init__(user_id, thread_id, jwt)

        self._api_adapter = api_adapter

    def run(self, **tool_input: Any) -> str:
        return self.render(self._api_adapter.get_notes(self.jwt))

    @staticmethod
    def render(notes: list[Note]) -> str:
        if not notes:
            return "The user has no notes."

        return "\n\n".join(f"# {note.title}\n{note.content}" for note in notes)
