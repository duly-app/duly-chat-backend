from typing import cast
from uuid import UUID

import pytest
from anthropic import Anthropic
from anthropic.types import MessageParam, TextBlock

from src.adapters.api.api_adapter import APIAdapter
from src.chatbot.approval import Decision
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.errors import MaxIterationsExceeded, ResponseTruncated
from src.chatbot.loop import chat_loop, resume_turn
from src.chatbot.loop_result import (
    ModelResult,
    StopReason,
    ToolResult,
    conversation_history,
)
from src.chatbot.loop_step import LoopContext
from src.chatbot.threads.tool_calls import unanswered_tool_calls
from src.chatbot.tools.registry import ToolRegistry, create_tool_registry
from tests.conftest import APIAdapterFactory
from tests.helpers.tokens import access_token
from tests.integration.conftest import AnthropicClientFactory
from tests.integration.fakes.fake_anthropic_client import FakeAnthropicClient
from tests.integration.fakes.fake_tools import with_testing_tools

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
THREAD_ID = UUID("550e8400-e29b-41d4-a716-4466554400aa")


def context(
    api: APIAdapter,
    client: FakeAnthropicClient,
    builder: ContextBuilder,
    history: list[MessageParam] | None = None,
    registry: ToolRegistry | None = None,
) -> LoopContext:
    """The dependencies a run needs, with this test's fakes in place."""
    return LoopContext(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        jwt=access_token(USER_ID),
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=builder,
        tool_registry=registry or create_tool_registry(api),
        history=history or [],
    )


def test_chat_loop_returns_assistant_answer_on_end_turn(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_1")

    outcome = chat_loop(
        context(api, client, context_builder), "How many notes do I have?"
    )

    result = outcome.result
    assert isinstance(result, ModelResult)
    assert result.stop_reason is StopReason.END_TURN
    assert outcome.usage.token_count == 165

    answer = result.content[0]
    assert isinstance(answer, TextBlock)
    assert answer.text.startswith("You have 5 notes")

    assert len(client.messages.calls) == 1

    system = client.messages.calls[0]["system"]
    assert "note-taking app" in system

    # Tools are declared through the tools parameter, not described in prose.
    assert "list_notes" not in system


def test_chat_loop_runs_a_tool_and_answers_from_its_output(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_2")

    outcome = chat_loop(
        context(api, client, context_builder), "Do I have a note about FastAPI?"
    )

    result = outcome.result
    assert isinstance(result, ModelResult)
    assert result.stop_reason is StopReason.END_TURN

    answer = result.content[0]
    assert isinstance(answer, TextBlock)
    assert answer.text.startswith("Yes — your FastAPI patterns note")

    # Two model calls with the tool run in between, which costs no tokens.
    assert len(client.messages.calls) == 2
    assert outcome.usage.token_count == 490

    # The second call carried the tool result back as a user message.
    second_call = client.messages.calls[1]["messages"]
    tool_result = second_call[-1]

    assert tool_result["role"] == "user"
    assert tool_result["content"][0]["type"] == "tool_result"
    assert tool_result["content"][0]["tool_use_id"] == "toolu_01"
    assert "FastAPI patterns" in tool_result["content"][0]["content"]

    # And the assistant's tool request sits just before it in the history.
    assert second_call[-2]["role"] == "assistant"


def test_the_tool_schemas_come_from_the_registry(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_1")

    chat_loop(
        context(
            api,
            client,
            context_builder,
            registry=with_testing_tools(create_tool_registry(api)),
        ),
        "How many notes do I have?",
    )

    tools = client.messages.calls[0]["tools"]

    assert [tool["name"] for tool in tools] == [
        "list_notes",
        "search_notes",
        "query_embedding_search",
        "get_note",
        "create_note",
        "update_note",
        "delete_note",
        "current_time",
        "sum",
    ]


def test_chat_loop_chains_two_tool_calls(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_2")
    client = anthropic_client("responses_3")

    outcome = chat_loop(
        context(
            api,
            client,
            context_builder,
            registry=with_testing_tools(create_tool_registry(api)),
        ),
        "I have a note somewhere with a bunch of groceries, "
        "could you tell me the total cost?",
    )

    result = outcome.result
    assert isinstance(result, ModelResult)
    assert result.stop_reason is StopReason.END_TURN

    answer = result.content[0]
    assert isinstance(answer, TextBlock)
    assert answer.text == "Your groceries note comes to 13.50."

    # Three model calls, two tool runs between them, and the tool runs are free.
    assert len(client.messages.calls) == 3
    assert outcome.usage.token_count == 930

    def tool_result_of(call_index: int) -> dict:
        return client.messages.calls[call_index]["messages"][-1]["content"][0]

    first_tool_output = tool_result_of(1)
    assert first_tool_output["tool_use_id"] == "toolu_01"
    assert "# Groceries" in first_tool_output["content"]

    second_tool_output = tool_result_of(2)
    assert second_tool_output["tool_use_id"] == "toolu_02"
    assert second_tool_output["content"] == "13.5"


def test_the_trajectory_records_every_step_and_derives_the_history(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_2")
    client = anthropic_client("responses_3")

    outcome = chat_loop(
        context(
            api,
            client,
            context_builder,
            registry=with_testing_tools(create_tool_registry(api)),
        ),
        "I have a note somewhere with a bunch of groceries, "
        "could you tell me the total cost?",
    )

    assert [type(step) for step in outcome.trajectory] == [
        ModelResult,
        ToolResult,
        ModelResult,
        ToolResult,
        ModelResult,
    ]

    assert [
        call.name
        for step in outcome.trajectory
        if isinstance(step, ModelResult)
        for call in step.tool_calls
    ] == ["list_notes", "sum"]

    # Only the model steps put messages on the wire; a tool result reaches the
    # model as the next step's sent message, so ToolResult contributes nothing.
    history = conversation_history(outcome.trajectory)
    assert [message["role"] for message in history] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]

    # The derived history is what actually went on the wire: the final model
    # call received all of it bar the reply it was about to give.
    assert history[:-1] == client.messages.calls[2]["messages"]

    assert outcome.result is outcome.trajectory[-1]


def test_chat_loop_sends_prior_history_before_the_new_message(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_1")

    earlier: list[MessageParam] = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi — how can I help?"},
    ]

    outcome = chat_loop(
        context(api, client, context_builder, earlier), "How many notes do I have?"
    )

    sent = client.messages.calls[0]["messages"]
    assert sent[:2] == earlier
    assert sent[2]["content"] == "How many notes do I have?"

    # The run's own record covers this turn only: the caller already holds
    # what came before, so returning it again would duplicate it in the store.
    first = outcome.trajectory[0]
    assert isinstance(first, ModelResult)
    assert conversation_history(outcome.trajectory) == [
        {"role": "user", "content": "How many notes do I have?"},
        first.received,
    ]


def test_chat_loop_rejects_a_truncated_response(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_4")

    with pytest.raises(ResponseTruncated):
        chat_loop(
            context(api, client, context_builder), "Summarise all my notes in detail."
        )

    # It gave up on the offending step instead of spending the whole budget.
    assert len(client.messages.calls) == 1


def test_chat_loop_gives_up_after_max_iterations(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_2")

    # responses_2 needs three steps to finish: model, tool, model. Two is one short.
    with pytest.raises(MaxIterationsExceeded):
        chat_loop(
            context(api, client, context_builder),
            "Do I have a note about FastAPI?",
            max_iterations=2,
        )

    # It stopped after the tool ran rather than calling the model again.
    assert len(client.messages.calls) == 1


def test_the_outcomes_answer_is_the_models_prose_without_tool_blocks(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_2")

    outcome = chat_loop(
        context(api, client, context_builder), "Do I have a note about FastAPI?"
    )

    # A plain string, so the client never parses content blocks or sees the
    # tool_use arguments that reached the model earlier in the turn.
    assert outcome.answer.startswith("Yes — your FastAPI patterns note")

    first = outcome.trajectory[0]
    assert isinstance(first, ModelResult)
    assert first.tool_calls and first.text == ""


class TestApproval:
    """A write stops the turn, and answering it carries on the same turn."""

    QUESTION = "Make a note called 'Dune' that says to read it."

    def test_a_turn_stops_with_the_action_it_wants_to_take(
        self,
        api_adapter: APIAdapterFactory,
        anthropic_client: AnthropicClientFactory,
        context_builder: ContextBuilder,
    ):
        api = api_adapter("db_1")

        outcome = chat_loop(
            context(api, anthropic_client("responses_5"), context_builder),
            self.QUESTION,
        )

        assert [action.name for action in outcome.pending] == ["create_note"]
        # Nothing to say yet, and nothing written.
        assert outcome.answer == ""
        assert "Dune" not in api.get_notes_by_keyword(access_token(USER_ID), "Dune")

    def test_the_assistant_message_is_kept_so_the_turn_can_resume(
        self,
        api_adapter: APIAdapterFactory,
        anthropic_client: AnthropicClientFactory,
        context_builder: ContextBuilder,
    ):
        api = api_adapter("db_1")

        outcome = chat_loop(
            context(api, anthropic_client("responses_5"), context_builder),
            self.QUESTION,
        )

        history = conversation_history(outcome.trajectory)
        calls = unanswered_tool_calls(history)

        assert history[-1]["role"] == "assistant"
        assert [call.name for call in calls] == ["create_note"]

    def test_approving_runs_the_tool_and_answers(
        self,
        api_adapter: APIAdapterFactory,
        anthropic_client: AnthropicClientFactory,
        context_builder: ContextBuilder,
    ):
        api = api_adapter("db_1")
        token = access_token(USER_ID)
        client = anthropic_client("responses_5")

        stopped = chat_loop(context(api, client, context_builder), self.QUESTION)
        assert len(stopped.pending) == 1
        history = conversation_history(stopped.trajectory)

        resumed = resume_turn(
            context(api, client, context_builder, history),
            unanswered_tool_calls(history),
            {"toolu_01": Decision(approved=True)},
        )

        assert resumed.answer == "Done — I made a note called Dune."
        assert resumed.pending == []
        assert api.get_notes_by_keyword(token, "Dune")

    def test_declining_leaves_the_notes_alone_and_still_answers(
        self,
        api_adapter: APIAdapterFactory,
        anthropic_client: AnthropicClientFactory,
        context_builder: ContextBuilder,
    ):
        api = api_adapter("db_1")
        token = access_token(USER_ID)
        client = anthropic_client("responses_5")

        stopped = chat_loop(context(api, client, context_builder), self.QUESTION)
        assert len(stopped.pending) == 1
        history = conversation_history(stopped.trajectory)

        resumed = resume_turn(
            context(api, client, context_builder, history),
            unanswered_tool_calls(history),
            {"toolu_01": Decision(approved=False, reason="Not yet")},
        )

        # The model still gets a turn to acknowledge it.
        assert resumed.answer
        assert api.get_notes_by_keyword(token, "Dune") == []

    def test_a_write_after_a_resume_stops_again(
        self,
        api_adapter: APIAdapterFactory,
        anthropic_client: AnthropicClientFactory,
        context_builder: ContextBuilder,
    ):
        # Approving one action is not approving the next: the resumed turn
        # asks for a second write and has to stop for that one too.
        api = api_adapter("db_1")
        client = anthropic_client("responses_6")
        question = "Add Dune to my reading list and rename the list."

        stopped = chat_loop(context(api, client, context_builder), question)
        history = conversation_history(stopped.trajectory)

        resumed = resume_turn(
            context(api, client, context_builder, history),
            unanswered_tool_calls(history),
            {"toolu_01": Decision(approved=True)},
        )

        assert [action.tool_use_id for action in resumed.pending] == ["toolu_02"]
        assert resumed.answer == ""

        # The first write did happen; only the second is waiting.
        token = access_token(USER_ID)
        assert api.get_notes_by_keyword(token, "Dune")
        assert api.get_notes_by_keyword(token, "Reading list 2026") == []

        history += conversation_history(resumed.trajectory)
        finished = resume_turn(
            context(api, client, context_builder, history),
            unanswered_tool_calls(history),
            {"toolu_02": Decision(approved=True)},
        )

        assert finished.answer == "Both notes are made."
        assert api.get_notes_by_keyword(token, "Reading list 2026")
