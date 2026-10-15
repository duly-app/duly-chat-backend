from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.chatbot.threads.thread_store import ThreadID
from src.chatbot.tools.tool import Tool
from src.domain.user import Token, UserID


class CurrentTime(Tool):
    """Tells the model what day it is, which it otherwise cannot know."""

    name = "current_time"
    description = (
        "The current date and time. Call this before filtering notes by date, "
        "to work out what a relative date like 'yesterday', 'this week' or "
        "'last month' refers to."
    )
    error_response = "Could not read the clock."
    input_schema = {"type": "object", "properties": {}}

    def __init__(
        self,
        timezone: ZoneInfo,
        user_id: UserID,
        thread_id: ThreadID,
        jwt: Token,
    ):
        super().__init__(user_id, thread_id, jwt)

        self._timezone = timezone

    def run(self, **tool_input: Any) -> str:
        now = datetime.now(self._timezone)

        return (
            f"{now.isoformat(timespec='seconds')}\n"
            f"Today is {now.strftime('%A, %d %B %Y')} ({now.tzname()})."
        )
