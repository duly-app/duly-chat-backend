from pathlib import Path
from typing import Callable, TypeAlias

import requests
from anthropic import Anthropic
from fastapi import Request

from src.adapters.security.jwt_token_service import JWTTokenService
from src.adapters.security.service_token_service import ServiceTokenService
from src.chatbot.context.context_block import SystemPromptBlock
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.threads.thread_store import ThreadStore
from src.env import ANTHROPIC_API_KEY, SERVICE_KEY, SIGNING_KEY, Env

ContextBuilderDependency: TypeAlias = Callable[[Request], ContextBuilder]
AnthropicClientDependency: TypeAlias = Callable[[Request], Anthropic]
TokenServiceDependency: TypeAlias = Callable[[Request], JWTTokenService]
ThreadStoreDependency: TypeAlias = Callable[[Request], ThreadStore]
ServiceTokenServiceDependency: TypeAlias = Callable[[Request], ServiceTokenService]
HTTPClientDependency: TypeAlias = Callable[[Request], requests.Session]
EnvDependency: TypeAlias = Callable[[Request], Env]


def create_context_builder() -> ContextBuilder:
    """Create and initialize the context builder with blocks."""
    context_dir = Path(__file__).parent / "chatbot" / "context"

    assert context_dir.exists(), f"Context directory {context_dir} does not exist"

    system_block = SystemPromptBlock()
    system_block.load_content(str(context_dir / "system_template.txt"))

    return ContextBuilder([system_block])


def create_anthropic_client(env: Env) -> Anthropic:
    return Anthropic(api_key=env[ANTHROPIC_API_KEY])


def create_token_service(env: Env) -> JWTTokenService:
    return JWTTokenService(env[SIGNING_KEY])


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

    app.state.env = env
    app.state.context_builder = create_context_builder()
    app.state.anthropic_client = create_anthropic_client(env)
    app.state.token_service = create_token_service(env)
    app.state.thread_store = create_thread_store()
    app.state.service_token_service = create_service_token_service(env)
    app.state.http_client = create_http_client()


def get_context_builder() -> ContextBuilderDependency:
    def _get(request: Request) -> ContextBuilder:
        return request.app.state.context_builder

    return _get


def get_anthropic_client() -> AnthropicClientDependency:
    def _get(request: Request) -> Anthropic:
        return request.app.state.anthropic_client

    return _get


def get_token_service() -> TokenServiceDependency:
    def _get(request: Request) -> JWTTokenService:
        return request.app.state.token_service

    return _get


def get_thread_store() -> ThreadStoreDependency:
    def _get(request: Request) -> ThreadStore:
        return request.app.state.thread_store

    return _get


def get_service_token_service() -> ServiceTokenServiceDependency:
    def _get(request: Request) -> ServiceTokenService:
        return request.app.state.service_token_service

    return _get


def get_http_client() -> HTTPClientDependency:
    def _get(request: Request) -> requests.Session:
        return request.app.state.http_client

    return _get


def get_env() -> EnvDependency:
    def _get(request: Request) -> Env:
        return request.app.state.env

    return _get
