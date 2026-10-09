import os
from pathlib import Path
from typing import Callable, TypeAlias

import requests
from anthropic import Anthropic
from fastapi import Request

from src.adapters.security.jwt_token_service import JWTTokenService
from src.adapters.security.service_token_service import ServiceTokenService
from src.chatbot.context.context_block import SystemPromptBlock, ToolsBlock
from src.chatbot.context.context_builder import ContextBuilder
from src.chatbot.threads.thread_store import ThreadStore

ContextBuilderDependency: TypeAlias = Callable[[Request], ContextBuilder]
AnthropicClientDependency: TypeAlias = Callable[[Request], Anthropic]
TokenServiceDependency: TypeAlias = Callable[[Request], JWTTokenService]
ThreadStoreDependency: TypeAlias = Callable[[Request], ThreadStore]
ServiceTokenServiceDependency: TypeAlias = Callable[[Request], ServiceTokenService]
HTTPClientDependency: TypeAlias = Callable[[Request], requests.Session]


def create_context_builder() -> ContextBuilder:
    """Create and initialize the context builder with blocks."""
    context_dir = Path(__file__).parent / "chatbot" / "context"

    assert context_dir.exists(), f"Context directory {context_dir} does not exist"

    system_block = SystemPromptBlock()
    system_block.load_content(str(context_dir / "system_template.txt"))

    tools_block = ToolsBlock()
    tools_block.load_content(str(context_dir / "tools_template.txt"))

    return ContextBuilder([system_block, tools_block])


def create_anthropic_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


def create_token_service() -> JWTTokenService:
    signing_key = os.getenv("SIGNING_KEY")
    if not signing_key:
        raise RuntimeError("SIGNING_KEY environment variable not set")
    return JWTTokenService(signing_key)


def create_http_client() -> requests.Session:
    """One session for the process, so connections to the notes service are
    pooled rather than re-handshaked on every request.
    """
    return requests.Session()


def create_service_token_service() -> ServiceTokenService:
    service_key = os.getenv("SERVICE_KEY")
    if not service_key:
        raise RuntimeError("SERVICE_KEY environment variable not set")
    if service_key == os.getenv("SIGNING_KEY"):
        raise RuntimeError("SERVICE_KEY must not be the same as SIGNING_KEY")
    return ServiceTokenService(service_key)


def create_thread_store() -> ThreadStore:
    """One store for the whole process, so threads outlive a single request."""
    return ThreadStore()


def setup_dependencies(app):
    app.state.context_builder = create_context_builder()
    app.state.anthropic_client = create_anthropic_client()
    app.state.token_service = create_token_service()
    app.state.thread_store = create_thread_store()
    app.state.service_token_service = create_service_token_service()
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
