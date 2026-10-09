import os
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.adapters.api.duly_api import DulyAPI
from src.adapters.security.jwt_token_service import JWTTokenService
from src.bootstrap import setup_dependencies
from src.chatbot.loop import chat_loop
from src.chatbot.loop_result import conversation_history
from src.chatbot.threads.thread_store import record_turn
from src.chatbot.tools.registry import create_tool_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_dependencies(app)
    yield


app = FastAPI(title="Duly Chat Backend", lifespan=lifespan)

security = HTTPBearer()


def get_token_service() -> JWTTokenService:
    signing_key = os.getenv("SIGNING_KEY", "")

    return JWTTokenService(signing_key)


def get_api_adapter(
    token_service: JWTTokenService = Depends(get_token_service),
) -> DulyAPI:
    service_uri = os.getenv("DULY_SERVICE_URI", "http://localhost:8001")
    return DulyAPI(service_uri, token_service)


@app.post("/threads/{thread_id}/messages")
async def chat(
    thread_id: UUID,
    message: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: JWTTokenService = Depends(get_token_service),
    api_adapter: DulyAPI = Depends(get_api_adapter),
):
    payload = token_service.decode_token(credentials.credentials)
    if not payload:
        return {"error": "Invalid token"}, 401

    user_id = UUID(payload["sub"])

    with record_turn(request.app.state.thread_store, user_id, thread_id) as thread:
        outcome = chat_loop(
            user_id=user_id,
            thread_id=thread_id,
            message=message,
            jwt=credentials.credentials,
            api_adapter=api_adapter,
            anthropic_client=request.app.state.anthropic_client,
            context_builder=request.app.state.context_builder,
            tool_registry=create_tool_registry(api_adapter),
            history=thread.messages,
        )

        thread.extend(conversation_history(outcome.trajectory))

    return {
        "thread_id": str(thread_id),
        "response": outcome.result,
        "token_usage": outcome.usage.token_count,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
