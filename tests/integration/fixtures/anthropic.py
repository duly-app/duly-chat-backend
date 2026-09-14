from pathlib import Path
from typing import Callable, TypeAlias

import pytest

from tests.integration.fakes.fake_anthropic_client import FakeAnthropicClient
from tests.integration.helpers.response_machine import ResponseMachine

RESPONSES = Path(__file__).parent.parent / "responses"

ResponsesName: TypeAlias = str

AnthropicClientFactory: TypeAlias = Callable[[ResponsesName], FakeAnthropicClient]


def create_anthropic_client(responses_name: ResponsesName) -> FakeAnthropicClient:
    responses_path = RESPONSES / f"{responses_name}.json"
    assert responses_path.exists(), f"Responses file does not exist: {responses_path}"

    return FakeAnthropicClient(ResponseMachine(responses_path))


@pytest.fixture
def anthropic_client() -> AnthropicClientFactory:
    def _anthropic_client(responses_name: ResponsesName) -> FakeAnthropicClient:
        return create_anthropic_client(responses_name)

    return _anthropic_client
