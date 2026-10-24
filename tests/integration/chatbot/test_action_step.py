from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import requests
from anthropic.types import ToolUseBlock

from src.chatbot.approval import DECLINED, Decision
from src.chatbot.loop_result import ApprovalRequired, StepResult, ToolResult
from src.chatbot.loop_step import ActionStep, LoopContext
from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.registry import RegisteredTool, create_tool_registry
from tests.conftest import APIAdapterFactory
from tests.helpers.tokens import access_token

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
    adapter = api_adapter("db_1")
    registry = create_tool_registry(adapter)

    for tool_class in (Exploding, Silent):
        registry[tool_class.name] = RegisteredTool(
            schema=tool_class.schema(), create=lambda *a, t=tool_class: t(adapter, *a)
        )

    return LoopContext(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        turn_id=TURN_ID,
        jwt=access_token(USER_ID),
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


def call(name: str, call_id: str = "toolu_1", **tool_input: Any) -> ToolUseBlock:
    return ToolUseBlock(id=call_id, name=name, input=tool_input, type="tool_use")


class TestApprovalGating:
    def test_a_write_waits_for_the_user(self, api_adapter: APIAdapterFactory):
        step = ActionStep([call("delete_note", note_id=str(uuid4()))])

        result, _ = step.execute(context(api_adapter))

        assert isinstance(result, ApprovalRequired)
        assert [action.name for action in result.pending] == ["delete_note"]
        assert result.pending[0].tool_use_id == "toolu_1"

    def test_the_pending_action_carries_what_was_asked_for(
        self, api_adapter: APIAdapterFactory
    ):
        # The user has to see the actual input to approve it meaningfully.
        step = ActionStep([call("create_note", title="Dune", content="Read it")])

        result, _ = step.execute(context(api_adapter))

        assert isinstance(result, ApprovalRequired)
        assert result.pending[0].input == {"title": "Dune", "content": "Read it"}

    def test_a_read_runs_without_asking(self, api_adapter: APIAdapterFactory):
        step = ActionStep([call("list_notes")])

        result, _ = step.execute(context(api_adapter))

        assert isinstance(result, ToolResult)

    def test_nothing_runs_while_one_call_waits(self, api_adapter: APIAdapterFactory):
        # The whole batch waits, so resuming can run each tool exactly once
        # instead of re-running the read or remembering its result.
        ctx = context(api_adapter)
        step = ActionStep(
            [
                call("list_notes", call_id="t1"),
                call("delete_note", call_id="t2", note_id=str(uuid4())),
            ]
        )

        result, _ = step.execute(ctx)

        assert isinstance(result, ApprovalRequired)
        assert [action.tool_use_id for action in result.pending] == ["t2"]

    def test_an_approved_write_runs(self, api_adapter: APIAdapterFactory):
        ctx = context(api_adapter)
        created = ActionStep(
            [call("create_note", title="Dune", content="Read it")],
            {"toolu_1": Decision(approved=True)},
        )

        result, _ = created.execute(ctx)

        assert isinstance(result, ToolResult)
        assert result_blocks(result)[0]["content"].startswith('Created "Dune"')

    def test_a_declined_write_does_not_run_and_says_so(
        self, api_adapter: APIAdapterFactory
    ):
        ctx = context(api_adapter)
        step = ActionStep(
            [call("create_note", title="Dune", content="Read it")],
            {"toolu_1": Decision(approved=False)},
        )

        result, _ = step.execute(ctx)
        block = result_blocks(result)[0]

        assert block["content"] == DECLINED
        # Not an error: the user declining is a fact, not a malfunction.
        assert "is_error" not in block

        titles = ActionStep([call("list_notes")]).execute(ctx)[0]
        assert "Dune" not in result_blocks(titles)[0]["content"]

    def test_a_reason_reaches_the_model(self, api_adapter: APIAdapterFactory):
        step = ActionStep(
            [call("delete_note", note_id=str(uuid4()))],
            {"toolu_1": Decision(approved=False, reason="Archive it instead")},
        )

        result, _ = step.execute(context(api_adapter))

        assert "Archive it instead" in result_blocks(result)[0]["content"]

    def test_an_unknown_tool_is_not_gated(self, api_adapter: APIAdapterFactory):
        # Reporting that the tool does not exist tells the model more than
        # asking the user to approve a call that cannot run.
        step = ActionStep([call("no_such_tool")])

        result, _ = step.execute(context(api_adapter))

        assert isinstance(result, ToolResult)
        assert result_blocks(result)[0]["is_error"] is True

    def test_two_writes_in_one_batch_are_asked_about_together(
        self, api_adapter: APIAdapterFactory
    ):
        # One prompt covering both, answered in one request: approving them
        # separately would run the first while the second was still waiting.
        step = ActionStep(
            [
                call("create_note", call_id="t1", title="Dune", content="Read it"),
                call("delete_note", call_id="t2", note_id=str(uuid4())),
            ]
        )

        result, _ = step.execute(context(api_adapter))

        assert isinstance(result, ApprovalRequired)
        assert [action.tool_use_id for action in result.pending] == ["t1", "t2"]

    def test_answering_only_one_of_two_leaves_both_waiting(
        self, api_adapter: APIAdapterFactory
    ):
        ctx = context(api_adapter)
        calls = [
            call("create_note", call_id="t1", title="Dune", content="Read it"),
            call("delete_note", call_id="t2", note_id=str(uuid4())),
        ]

        result, _ = ActionStep(calls, {"t1": Decision(approved=True)}).execute(ctx)

        # The approved one has not run: a partially answered batch runs nothing.
        assert isinstance(result, ApprovalRequired)
        assert [action.tool_use_id for action in result.pending] == ["t2"]

        listed = ActionStep([call("list_notes")]).execute(ctx)[0]
        assert "Dune" not in result_blocks(listed)[0]["content"]
