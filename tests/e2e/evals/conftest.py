import pytest
from anthropic import Anthropic

from tests.e2e.evals.runner import live_client


@pytest.fixture(scope="session")
def live_anthropic_client() -> Anthropic:
    try:
        return live_client()
    except RuntimeError as error:
        pytest.skip(str(error))
