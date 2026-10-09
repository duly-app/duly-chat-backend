from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.adapters.api.duly_api import DulyAPI
from src.adapters.security.jwt_token_service import JWTTokenService
from src.bootstrap import setup_dependencies
from src.chatbot.loop import chat_loop
from src.chatbot.loop_result import conversation_history
from src.chatbot.threads.thread_store import record_turn
from src.chatbot.tools.registry import create_tool_registry
from src.env import DULY_SERVICE_URI, Env, OSEnv

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


security = HTTPBearer()


def get_token_service(request: Request) -> JWTTokenService:
    return request.app.state.token_service


def get_api_adapter(
    request: Request,
    token_service: JWTTokenService = Depends(get_token_service),
) -> DulyAPI:
    service_uri = request.app.state.env[DULY_SERVICE_URI]

    return DulyAPI(
        service_uri,
        token_service,
        request.app.state.service_token_service,
        request.app.state.http_client,
    )


@router.post("/threads/{thread_id}/messages")
async def chat(
    thread_id: UUID,
    body: ChatRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: JWTTokenService = Depends(get_token_service),
    api_adapter: DulyAPI = Depends(get_api_adapter),
):
    payload = token_service.decode_token(credentials.credentials)
    if not payload:
        # Raised, not returned: FastAPI has no tuple convention, so returning
        # (body, 401) ships the pair as a 200.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user_id = UUID(payload["sub"])

    with record_turn(request.app.state.thread_store, user_id, thread_id) as thread:
        outcome = chat_loop(
            user_id=user_id,
            thread_id=thread_id,
            message=body.message,
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


@router.get("/health")
async def health():
    return {"status": "ok"}


def create_app(env: Env | None = None) -> FastAPI:
    environment = env or OSEnv()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        setup_dependencies(application, environment)
        yield

    application = FastAPI(title="Duly Chat Backend", lifespan=lifespan)
    application.include_router(router)

    return application


app = create_app()
