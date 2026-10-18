from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from anthropic import Anthropic

from src.adapters.security.service_token_service import ServiceTokenService
from src.adapters.security.token_service import TokenService
from src.chatbot.context.context_block import SystemPromptBlock
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.threads.thread_store import ThreadStore
from src.env import (
    ANTHROPIC_API_KEY,
    LOG_LEVEL,
    SERVICE_KEY,
    SIGNING_KEY,
    TIMEZONE,
    Env,
)
from src.logs import configure as configure_logging

CONTEXT_DIR = Path(__file__).parent / "chatbot" / "context"
SYSTEM_TEMPLATE = CONTEXT_DIR / "system_template.txt"


def create_context_builder(system_template: Path | None = None) -> ContextBuilder:
    """Create and initialize the context builder with blocks."""
    template = system_template or SYSTEM_TEMPLATE

    assert template.exists(), f"System template {template} does not exist"

    system_block = SystemPromptBlock()
    system_block.load_content(str(template))

    return ContextBuilder([system_block])


def create_anthropic_client(env: Env) -> Anthropic:
    return Anthropic(api_key=env[ANTHROPIC_API_KEY])


def create_token_service(env: Env) -> TokenService:
    return TokenService(env[SIGNING_KEY])


def create_http_client() -> requests.Session:
    """One session for the process, so connections to the notes service are
    pooled rather than re-handshaked on every request.
    """
    return requests.Session()


def create_service_token_service(env: Env) -> ServiceTokenService:
    return ServiceTokenService(env[SERVICE_KEY])


def create_thread_store() -> ThreadStore:
    """One store for the whole process, so threads outlive a single request."""
    return ThreadStore()


def setup_dependencies(app, env: Env) -> None:
    """Validate the environment before building anything that depends on it."""
    env.validate()

    configure_logging(env[LOG_LEVEL])

    app.state.env = env
    app.state.context_builder = create_context_builder()
    app.state.anthropic_client = create_anthropic_client(env)
    app.state.token_service = create_token_service(env)
    app.state.thread_store = create_thread_store()
    app.state.service_token_service = create_service_token_service(env)
    app.state.http_client = create_http_client()
    app.state.timezone = ZoneInfo(env[TIMEZONE])
