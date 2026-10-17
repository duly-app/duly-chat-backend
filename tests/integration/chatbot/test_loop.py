from typing import cast
from uuid import UUID

import pytest
from anthropic import Anthropic
from anthropic.types import MessageParam, TextBlock

from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.errors import MaxIterationsExceeded, ResponseTruncated
from src.chatbot.loop import chat_loop
from src.chatbot.loop_result import (
    ModelResult,
    StopReason,
    ToolResult,
    conversation_history,
)
from src.chatbot.tools.registry import create_tool_registry
from tests.integration.conftest import AnthropicClientFactory, APIAdapterFactory
from tests.integration.fakes.fake_tools import with_testing_tools
from tests.integration.helpers.tokens import access_token

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
THREAD_ID = UUID("550e8400-e29b-41d4-a716-4466554400aa")


def test_chat_loop_returns_assistant_answer_on_end_turn(
    api_adapter: APIAdapterFactory,
    anthropic_client: AnthropicClientFactory,
    context_builder: ContextBuilder,
):
    api = api_adapter("db_1")
    client = anthropic_client("responses_1")
    token = access_token(USER_ID)

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message="How many notes do I have?",
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=create_tool_registry(api),
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
    token = access_token(USER_ID)

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message="Do I have a note about FastAPI?",
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=create_tool_registry(api),
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
    token = access_token(USER_ID)

    chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message="How many notes do I have?",
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=with_testing_tools(create_tool_registry(api)),
    )

    tools = client.messages.calls[0]["tools"]

    assert [tool["name"] for tool in tools] == [
        "list_notes",
        "search_notes",
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
    token = access_token(USER_ID)

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message=(
            "I have a note somewhere with a bunch of groceries, "
            "could you tell me the total cost?"
        ),
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=with_testing_tools(create_tool_registry(api)),
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
    token = access_token(USER_ID)

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message=(
            "I have a note somewhere with a bunch of groceries, "
            "could you tell me the total cost?"
        ),
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=with_testing_tools(create_tool_registry(api)),
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
    token = access_token(USER_ID)

    earlier: list[MessageParam] = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi — how can I help?"},
    ]

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message="How many notes do I have?",
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=create_tool_registry(api),
        history=earlier,
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
    token = access_token(USER_ID)

    with pytest.raises(ResponseTruncated):
        chat_loop(
            user_id=USER_ID,
            thread_id=THREAD_ID,
            message="Summarise all my notes in detail.",
            jwt=token,
            api_adapter=api,
            anthropic_client=cast(Anthropic, client),
            context_builder=context_builder,
            tool_registry=create_tool_registry(api),
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
    token = access_token(USER_ID)

    # responses_2 needs three steps to finish: model, tool, model. Two is one short.
    with pytest.raises(MaxIterationsExceeded):
        chat_loop(
            user_id=USER_ID,
            thread_id=THREAD_ID,
            message="Do I have a note about FastAPI?",
            jwt=token,
            api_adapter=api,
            anthropic_client=cast(Anthropic, client),
            context_builder=context_builder,
            tool_registry=create_tool_registry(api),
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
    token = access_token(USER_ID)

    outcome = chat_loop(
        user_id=USER_ID,
        thread_id=THREAD_ID,
        message="Do I have a note about FastAPI?",
        jwt=token,
        api_adapter=api,
        anthropic_client=cast(Anthropic, client),
        context_builder=context_builder,
        tool_registry=create_tool_registry(api),
    )

    # A plain string, so the client never parses content blocks or sees the
    # tool_use arguments that reached the model earlier in the turn.
    assert outcome.answer.startswith("Yes — your FastAPI patterns note")

    first = outcome.trajectory[0]
    assert isinstance(first, ModelResult)
    assert first.tool_calls and first.text == ""
