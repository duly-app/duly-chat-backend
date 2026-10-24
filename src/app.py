from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any, Callable
from uuid import UUID

from anthropic.types import ToolUseBlock
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from src.adapters.api.duly_api import DulyAPI
from src.adapters.security.token_service import TokenService
from src.bootstrap import setup_dependencies
from src.chatbot.approval import Decision, Decisions
from src.chatbot.loop import chat_loop, resume_turn
from src.chatbot.loop_result import LoopOutcome, conversation_history
from src.chatbot.loop_step import LoopContext
from src.chatbot.threads.thread_store import new_turn_id, record_turn
from src.chatbot.threads.tool_calls import unanswered_tool_calls
from src.chatbot.tools.registry import create_tool_registry, requires_approval
from src.chatbot.trace import log_turn, log_turn_failed
from src.env import DULY_SERVICE_URI, Env, OSEnv

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class PendingActionResponse(BaseModel):
    tool_use_id: str
    name: str
    input: dict[str, Any]


class DecisionRequest(BaseModel):
    tool_use_id: str
    approved: bool
    reason: str = ""


class ApprovalRequest(BaseModel):
    decisions: list[DecisionRequest]


class ChatResponse(BaseModel):
    thread_id: UUID
    message: str
    token_usage: int
    pending: list[PendingActionResponse] = []


security = HTTPBearer()


def get_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def get_api_adapter(request: Request) -> DulyAPI:
    service_uri = request.app.state.env[DULY_SERVICE_URI]

    return DulyAPI(
        service_uri,
        request.app.state.service_token_service,
        request.app.state.http_client,
    )


def authenticated_user(
    credentials: HTTPAuthorizationCredentials, token_service: TokenService
) -> UUID:
    payload = token_service.decode_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    return UUID(payload["sub"])


def run_turn(
    request: Request,
    user_id: UUID,
    thread_id: UUID,
    jwt: str,
    prompt: str,
    run: Callable[[LoopContext], LoopOutcome],
) -> LoopOutcome:
    """Run one turn against a stored thread, logging however it ends.

    Shared by starting a turn and resuming one: only `run` differs, and it is
    handed the same context either way.
    """
    turn_id = new_turn_id()
    started = perf_counter()
    api_adapter = get_api_adapter(request)

    try:
        with record_turn(request.app.state.thread_store, user_id, thread_id) as thread:
            outcome = run(
                LoopContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    jwt=jwt,
                    api_adapter=api_adapter,
                    anthropic_client=request.app.state.anthropic_client,
                    context_builder=request.app.state.context_builder,
                    tool_registry=create_tool_registry(
                        api_adapter, request.app.state.timezone
                    ),
                    history=thread.messages,
                    turn_id=turn_id,
                )
            )

            thread.extend(conversation_history(outcome.trajectory))
    except Exception as error:
        log_turn_failed(
            turn_id=turn_id,
            user_id=user_id,
            thread_id=thread_id,
            prompt=prompt,
            error=error,
            seconds=perf_counter() - started,
        )
        raise

    log_turn(
        turn_id=turn_id,
        user_id=user_id,
        thread_id=thread_id,
        prompt=prompt,
        outcome=outcome,
        seconds=perf_counter() - started,
    )

    return outcome


def as_response(thread_id: UUID, outcome: LoopOutcome) -> ChatResponse:
    return ChatResponse(
        thread_id=thread_id,
        message=outcome.answer,
        token_usage=outcome.usage.token_count,
        pending=[
            PendingActionResponse(
                tool_use_id=action.tool_use_id, name=action.name, input=action.input
            )
            for action in outcome.pending
        ],
    )


@router.post("/threads/{thread_id}/messages", response_model=ChatResponse)
async def chat(
    thread_id: UUID,
    body: ChatRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: TokenService = Depends(get_token_service),
):
    user_id = authenticated_user(credentials, token_service)

    outcome = run_turn(
        request,
        user_id,
        thread_id,
        jwt=credentials.credentials,
        prompt=body.message,
        run=lambda context: chat_loop(context, body.message),
    )

    return as_response(thread_id, outcome)


@router.post("/threads/{thread_id}/approvals", response_model=ChatResponse)
def approvals(
    thread_id: UUID,
    body: ApprovalRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: TokenService = Depends(get_token_service),
    api_adapter: DulyAPI = Depends(get_api_adapter),
):
    """Answer the actions a turn stopped for, and carry that turn on.

    The decisions name tool calls by id; what runs is read from the stored
    thread, never from this request, so the action taken is the one the user
    was shown.
    """
    user_id = authenticated_user(credentials, token_service)
    registry = create_tool_registry(api_adapter, request.app.state.timezone)

    stored = request.app.state.thread_store.load(user_id, thread_id)
    unanswered = unanswered_tool_calls(stored.messages)
    needs_approval = [
        call.id for call in unanswered if requires_approval(registry, call.name)
    ]

    if not needs_approval:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This thread is not waiting on an approval",
        )

    decisions = {
        decision.tool_use_id: Decision(
            approved=decision.approved, reason=decision.reason
        )
        for decision in body.decisions
    }

    if set(needs_approval) != set(decisions):
        # Every pending action, and nothing else: a partial answer would run
        # some of a batch, and an unknown id is a client working from a stale
        # view of the thread.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decide exactly the actions this thread is waiting on",
        )

    outcome = run_turn(
        request,
        user_id,
        thread_id,
        jwt=credentials.credentials,
        prompt=approval_prompt(unanswered, decisions),
        run=lambda context: resume_turn(context, unanswered, decisions),
    )

    return as_response(thread_id, outcome)


def approval_prompt(calls: list[ToolUseBlock], decisions: Decisions) -> str:
    """What the turn log shows in place of a user message."""
    answered = [
        f"{'approved' if decisions[call.id].approved else 'declined'} {call.name}"
        for call in calls
        if call.id in decisions
    ]

    return ", ".join(answered)


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
    register_metrics(application)

    return application


def register_metrics(application: FastAPI) -> None:
    """Exposes /metrics for Prometheus to scrape.

    The handler label is the route template, so the thread id in the path does
    not leak into the label set. The registry is per app rather than the
    process-wide default one, so building several apps in a test run doesn't
    collide on already-registered metrics.
    """
    instrumentator = Instrumentator(registry=CollectorRegistry())
    instrumentator.instrument(application).expose(application)


app = create_app()
