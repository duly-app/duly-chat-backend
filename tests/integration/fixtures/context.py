import pytest

from src.bootstrap import create_context_builder
from src.chatbot.context.context_builder import ContextBuilder


@pytest.fixture
def context_builder() -> ContextBuilder:
    return create_context_builder()
