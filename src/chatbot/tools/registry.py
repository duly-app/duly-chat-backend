from dataclasses import dataclass
from functools import partial
from typing import Callable, TypeAlias
from zoneinfo import ZoneInfo

from anthropic.types import ToolParam

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.threads.thread_store import ThreadID
from src.chatbot.tools.create_note import CreateNote
from src.chatbot.tools.current_time import CurrentTime
from src.chatbot.tools.delete_note import DeleteNote
from src.chatbot.tools.get_note import GetNote
from src.chatbot.tools.list_notes import ListNotes
from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.search_notes import SearchNotes
from src.chatbot.tools.tool import Tool
from src.chatbot.tools.update_note import UpdateNote
from src.domain.user import Token, UserID

ToolConstructor: TypeAlias = Callable[[UserID, ThreadID, Token], Tool]

NOTES_TOOLS: tuple[type[NotesTool], ...] = (
    ListNotes,
    SearchNotes,
    GetNote,
    CreateNote,
    UpdateNote,
    DeleteNote,
)


@dataclass(frozen=True)
class RegisteredTool:
    schema: ToolParam
    create: ToolConstructor


ToolRegistry: TypeAlias = dict[str, RegisteredTool]


def create_tool_registry(
    api_adapter: APIAdapter, timezone: ZoneInfo | None = None
) -> ToolRegistry:
    """The tools this app offers, each with its app-scoped dependency curried in."""
    zone = timezone or ZoneInfo("UTC")
    notes_tools = {
        tool.name: RegisteredTool(
            schema=tool.schema(), create=partial(tool, api_adapter)
        )
        for tool in NOTES_TOOLS
    }

    return {
        **notes_tools,
        CurrentTime.name: RegisteredTool(
            schema=CurrentTime.schema(), create=partial(CurrentTime, zone)
        ),
    }
