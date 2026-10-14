from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import requests
from anthropic.types import ToolUseBlock

from src.chatbot.loop_result import StepResult, ToolResult
from src.chatbot.loop_step import ActionStep, LoopContext
from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.registry import RegisteredTool, create_tool_registry
from tests.integration.conftest import APIAdapterFactory
from tests.integration.fakes.fake_token_service import FakeTokenService

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
THREAD_ID = UUID("550e8400-e29b-41d4-a716-4466554400aa")
TURN_ID = UUID("550e8400-e29b-41d4-a716-4466554400bb")


class Exploding(NotesTool):
    name = "exploding"
    description = "Fails the way an unreachable notes service does."
    error_response = "Could not reach the notes service."
    input_schema = {"type": "object", "properties": {}}

    def run(self, **tool_input: Any) -> str:
        raise requests.ConnectionError("http://duly-backend:5000/api/notes")


class Silent(NotesTool):
    name = "silent"
    description = "Returns nothing at all."
    error_response = "Could not reach the notes service."
    input_schema = {"type": "object", "properties": {}}

    def run(self, **tool_input: Any) -> str:
        return ""


def context(api_adapter: APIAdapterFactory) -> LoopContext:
    adapter = api_adapter("db_1", "test-secret")
    registry = create_tool_registry(adapter)

    for tool_class in (Exploding, Silent):
        registry[tool_class.name] = RegisteredTool(
            schema=tool_class.schema(), create=lambda *a, t=tool_class: t(adapter, *a)
        )

    return LoopContext(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        turn_id=TURN_ID,
        jwt=FakeTokenService.create_fake_token(USER_ID),
        history=[],
        trajectory=[],
        api_adapter=adapter,
        anthropic_client=None,  # type: ignore[arg-type]
        context_builder=None,  # type: ignore[arg-type]
        tool_registry=registry,
    )


def result_blocks(result: StepResult) -> list[dict[str, Any]]:
    """The tool_result blocks, as plain dicts.

    content is typed as a union of every block param the API accepts, so it
    needs narrowing before it can be indexed.
    """
    assert isinstance(result, ToolResult)
    content = cast(list[Any], result.tool_result_message["content"])

    return [dict(block) for block in content]


def result_block(ctx: LoopContext, name: str) -> dict[str, Any]:
    step = ActionStep(
        [ToolUseBlock(id="toolu_1", name=name, input={}, type="tool_use")]
    )
    result, usage = step.execute(ctx)

    assert usage.token_count == 0

    return result_blocks(result)[0]


def test_a_tool_that_raises_is_reported_to_the_model(api_adapter: APIAdapterFactory):
    block = result_block(context(api_adapter), "exploding")

    # Reported, not raised: an exception here would lose the whole turn.
    assert block["is_error"] is True
    assert block["content"].startswith("Could not reach the notes service.")
    assert "ConnectionError" in block["content"]


def test_a_failure_does_not_leak_the_internal_url(api_adapter: APIAdapterFactory):
    block = result_block(context(api_adapter), "exploding")

    # The requests error carries the service address; the user can read this.
    assert "duly-backend" not in block["content"]
    assert "5000" not in block["content"]


def test_an_empty_tool_result_is_replaced(api_adapter: APIAdapterFactory):
    block = result_block(context(api_adapter), "silent")

    # The API rejects empty content blocks, so an empty return would fail the
    # turn at the API with nothing to point at.
    assert block["content"]
    assert block["is_error"] is True


def test_an_unknown_tool_is_reported_to_the_model(api_adapter: APIAdapterFactory):
    block = result_block(context(api_adapter), "no_such_tool")

    assert block["is_error"] is True
    assert block["content"] == "No such tool: no_such_tool"


def test_one_failing_tool_does_not_sink_the_others(api_adapter: APIAdapterFactory):
    step = ActionStep(
        [
            ToolUseBlock(id="t1", name="exploding", input={}, type="tool_use"),
            ToolUseBlock(id="t2", name="list_notes", input={}, type="tool_use"),
        ]
    )

    result, _ = step.execute(context(api_adapter))
    blocks = result_blocks(result)

    assert blocks[0]["is_error"] is True
    assert "5 notes." in blocks[1]["content"]


def test_a_tool_without_an_error_response_cannot_be_defined():
    with pytest.raises(ValueError, match="error_response"):

        class Forgetful(NotesTool):
            name = "forgetful"
            description = "Declares no error response."
            input_schema = {"type": "object", "properties": {}}

            def run(self, **tool_input: Any) -> str:
                return str(uuid4())
