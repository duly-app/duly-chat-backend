from dataclasses import dataclass
from functools import partial
from typing import Callable, TypeAlias

from anthropic.types import ToolParam

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.tools.get_notes import GetNotes
from src.chatbot.tools.tool import Tool
from src.domain.user import Token, UserID

ToolConstructor: TypeAlias = Callable[[UserID, str, Token], Tool]


@dataclass(frozen=True)
class RegisteredTool:
    schema: ToolParam
    create: ToolConstructor


ToolRegistry: TypeAlias = dict[str, RegisteredTool]


def create_tool_registry(api_adapter: APIAdapter) -> ToolRegistry:
    return {
        GetNotes.name: RegisteredTool(
            schema=GetNotes.schema(), create=partial(GetNotes, api_adapter)
        ),
    }
