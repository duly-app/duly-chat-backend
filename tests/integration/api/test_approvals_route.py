from uuid import UUID

import pytest
from anthropic.types import ToolUseBlock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app import create_app
from src.chatbot.threads.thread_store import Thread
from tests.helpers.tokens import access_token
from tests.integration.fakes.fake_env import VALID_VALUES, FakeEnv
from tests.integration.fixtures.anthropic import create_anthropic_client

from src.env import SIGNING_KEY  # isort: skip

USER_ID = UUID("550e8400-e29b-41d4-a716-446655440099")
THREAD_ID = UUID("550e8400-e29b-41d4-a716-4466554400aa")

URL = f"/threads/{THREAD_ID}/approvals"

PENDING_CALL = ToolUseBlock(
    id="toolu_01",
    name="create_note",
    input={"title": "Dune", "content": "Read it"},
    type="tool_use",
)


@pytest.fixture
def app() -> FastAPI:
    return create_app(FakeEnv())


@pytest.fixture
def client(app: FastAPI):
    # Entered, so the lifespan has built app.state before a test reads it.
    with TestClient(app) as test_client:
        yield test_client


def token() -> str:
    return access_token(USER_ID, secret_key=VALID_VALUES[SIGNING_KEY])


def auth() -> dict[str, str]:
    return {"Authorization": f"Bearer {token()}"}


def awaiting_approval(app: FastAPI) -> None:
    """Seed a thread that stopped on a write, as a turn would leave it."""
    app.state.thread_store.save(
        Thread(
            user_id=USER_ID,
            thread_id=THREAD_ID,
            messages=[
                {"role": "user", "content": "Make a note called 'Dune'."},
                {"role": "assistant", "content": [PENDING_CALL]},
            ],
        )
    )


def test_an_invalid_token_is_rejected(client: TestClient):
    response = client.post(
        URL,
        json={"decisions": [{"tool_use_id": "toolu_01", "approved": True}]},
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_a_thread_that_is_not_waiting_is_a_conflict(client: TestClient):
    response = client.post(
        URL,
        json={"decisions": [{"tool_use_id": "toolu_01", "approved": True}]},
        headers=auth(),
    )

    assert response.status_code == 409


def test_an_unknown_tool_use_id_is_refused(client: TestClient, app: FastAPI):
    # A client working from a stale view of the thread, or one trying to
    # approve something the model never asked for.
    awaiting_approval(app)

    response = client.post(
        URL,
        json={"decisions": [{"tool_use_id": "toolu_99", "approved": True}]},
        headers=auth(),
    )

    assert response.status_code == 400


def test_a_partial_answer_is_refused(client: TestClient, app: FastAPI):
    awaiting_approval(app)

    response = client.post(URL, json={"decisions": []}, headers=auth())

    assert response.status_code == 400


def test_another_users_thread_is_not_visible(client: TestClient, app: FastAPI):
    # Threads are stored per user, so a stranger's token finds nothing to
    # approve rather than approving someone else's write.
    awaiting_approval(app)
    stranger = UUID("00000000-0000-0000-0000-000000000001")

    their_token = access_token(stranger, secret_key=VALID_VALUES[SIGNING_KEY])

    response = client.post(
        URL,
        json={"decisions": [{"tool_use_id": "toolu_01", "approved": True}]},
        headers={"Authorization": f"Bearer {their_token}"},
    )

    assert response.status_code == 409


def test_approving_runs_the_write_and_returns_the_answer(
    client: TestClient, app: FastAPI
):
    awaiting_approval(app)
    app.state.anthropic_client = create_anthropic_client("responses_5")

    response = client.post(
        URL,
        json={"decisions": [{"tool_use_id": "toolu_01", "approved": True}]},
        headers=auth(),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Done — I made a note called Dune."
    assert response.json()["pending"] == []


def test_declining_sends_the_reason_on(client: TestClient, app: FastAPI):
    awaiting_approval(app)
    app.state.anthropic_client = create_anthropic_client("responses_5")

    response = client.post(
        URL,
        json={
            "decisions": [
                {
                    "tool_use_id": "toolu_01",
                    "approved": False,
                    "reason": "Call it Dune (1965)",
                }
            ]
        },
        headers=auth(),
    )

    assert response.status_code == 200

    sent = app.state.anthropic_client.messages.calls[-1]["messages"][-1]
    assert "Call it Dune (1965)" in str(sent)
