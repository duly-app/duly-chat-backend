from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.threads.thread_store import ThreadID
from src.chatbot.tools.tool import Tool
from src.domain.notes import NoteID
from src.domain.user import Token, UserID


class NotesTool(Tool, abstract=True):
    """A tool that reaches the notes service on the user's behalf."""

    def __init__(
        self,
        api_adapter: APIAdapter,
        user_id: UserID,
        thread_id: ThreadID,
        jwt: Token,
    ):
        super().__init__(user_id, thread_id, jwt)

        self._api = api_adapter


def as_note_id(value: object) -> NoteID | None:
    """Parse a model-supplied id, which is a string and may be invented."""
    try:
        return NoteID(str(value))
    except (TypeError, ValueError):
        return None
