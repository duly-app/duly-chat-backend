"""Putting a case's question to the real model."""

from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from anthropic import Anthropic

from src.adapters.api.api_adapter import APIAdapter
from src.bootstrap import create_context_builder
from src.chatbot.loop import chat_loop
from src.chatbot.loop_result import LoopOutcome
from src.chatbot.tools.registry import ToolRegistry, create_tool_registry
from src.env import ANTHROPIC_API_KEY, OSEnv
from tests.conftest import create_api_adapter, create_note_db
from tests.e2e.evals.eval_case import EvalCase
from tests.helpers.tokens import access_token

USER_ID = UUID("7c9e6679-7425-40de-944b-e07fc1f90ae7")
TIMEZONE = ZoneInfo("UTC")


def run_case(case: EvalCase, client: Anthropic) -> LoopOutcome:
    adapter = create_api_adapter(create_note_db(case.db))

    return chat_loop(
        user_id=USER_ID,
        thread_id=uuid4(),
        message=case.question,
        jwt=access_token(USER_ID),
        api_adapter=adapter,
        anthropic_client=client,
        context_builder=create_context_builder(case.system_template),
        tool_registry=tool_registry(case, adapter),
    )


def tool_registry(case: EvalCase, adapter: APIAdapter) -> ToolRegistry:
    """The app's registry, narrowed to the tools the case allows."""
    registry = create_tool_registry(adapter, TIMEZONE)

    if case.available_tools is None:
        return registry

    allowed = {tool.name for tool in case.available_tools}

    return {name: tool for name, tool in registry.items() if name in allowed}


def live_client() -> Anthropic:
    """A client against the real API. Raises when there is no key to use."""
    env = OSEnv()

    if not env.get(ANTHROPIC_API_KEY):
        raise RuntimeError(f"{ANTHROPIC_API_KEY} is not set")

    return Anthropic(api_key=env[ANTHROPIC_API_KEY])
