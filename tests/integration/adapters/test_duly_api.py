from typing import Any
from uuid import uuid4

import jwt
import pytest

from src.adapters.api.duly_api import DulyAPI
from src.adapters.security.jwt_token_service import JWTTokenService
from src.adapters.security.service_token_service import (
    SERVICE_SUBJECT,
    SERVICE_TOKEN_HEADER,
    SERVICE_TOKEN_TYPE,
    ServiceTokenService,
)
from tests.integration.fakes.fake_http_client import FakeHTTPClient

# Long enough to keep pyjwt from warning about weak HMAC keys.
SERVICE_KEY = "service-key-that-is-at-least-32-bytes-long"
SIGNING_KEY = "signing-key-that-is-at-least-32-bytes-long"
USER_JWT = "user-jwt"

NOTE_RESPONSE = {
    "id": "550e8400-e29b-41d4-a716-446655440010",
    "title": "Groceries",
    "content": "Milk",
    "created_at": "2026-10-01T10:00:00+00:00",
    "last_updated": "2026-10-01T10:00:00+00:00",
    "last_author_type": "user",
}


@pytest.fixture
def http() -> FakeHTTPClient:
    return FakeHTTPClient(payload=NOTE_RESPONSE, collection_payload=[NOTE_RESPONSE])


@pytest.fixture
def api(http: FakeHTTPClient) -> DulyAPI:
    return DulyAPI(
        "http://notes",
        JWTTokenService(SIGNING_KEY),
        ServiceTokenService(SERVICE_KEY),
        http_client=http,
    )


def service_claims(call: dict[str, Any], key: str = SERVICE_KEY) -> dict[str, Any]:
    return jwt.decode(call["headers"][SERVICE_TOKEN_HEADER], key, algorithms=["HS256"])


def test_writes_carry_both_credentials(api: DulyAPI, http: FakeHTTPClient):
    api.create_note(USER_JWT, title="Groceries", content="Milk")

    headers = http.last_call["headers"]

    # The user's token says whose note it is; ours says what wrote it.
    assert headers["Authorization"] == f"Bearer {USER_JWT}"

    claims = service_claims(http.last_call)
    assert claims["sub"] == SERVICE_SUBJECT
    assert claims["type"] == SERVICE_TOKEN_TYPE

    # Short-lived, because it travels over plain HTTP internally: sniffing a
    # request buys a minute of replay, not permanent impersonation.
    assert claims["exp"] - claims["iat"] == 60


def test_the_service_credential_is_not_signed_with_the_user_key(
    api: DulyAPI, http: FakeHTTPClient
):
    api.create_note(USER_JWT, title="Groceries", content="Milk")

    # The whole point of two keys: leaking one must not forge the other.
    with pytest.raises(jwt.InvalidSignatureError):
        service_claims(http.last_call, key=SIGNING_KEY)


def test_updates_and_deletes_carry_it_too(api: DulyAPI, http: FakeHTTPClient):
    note_id = uuid4()

    api.update_note(USER_JWT, note_id, title="Shopping")

    assert SERVICE_TOKEN_HEADER in http.last_call["headers"]
    assert http.last_call["url"] == f"http://notes/notes/{note_id}"

    # Only the field being changed is sent, so the rest is left alone.
    assert http.last_call["json"] == {"title": "Shopping"}

    api.delete_note(USER_JWT, note_id)

    assert SERVICE_TOKEN_HEADER in http.last_call["headers"]
    assert http.last_call["verb"] == "delete"


def test_reads_do_not_carry_it(api: DulyAPI, http: FakeHTTPClient):
    api.get_notes(USER_JWT)

    # A read asserts no authorship, so it has no business holding the key.
    assert SERVICE_TOKEN_HEADER not in http.last_call["headers"]
    assert http.last_call["url"] == "http://notes/notes"

    api.get_notes_by_keyword(USER_JWT, "milk")

    assert SERVICE_TOKEN_HEADER not in http.last_call["headers"]
    assert http.last_call["params"] == {"keyword": "milk"}


def test_each_write_mints_a_fresh_credential(api: DulyAPI, http: FakeHTTPClient):
    api.create_note(USER_JWT, title="One", content="")
    api.create_note(USER_JWT, title="Two", content="")

    first, second = (call["headers"][SERVICE_TOKEN_HEADER] for call in http.calls)

    # Not a long-lived secret held in memory and reused forever.
    assert jwt.decode(first, SERVICE_KEY, algorithms=["HS256"])["exp"]
    assert jwt.decode(second, SERVICE_KEY, algorithms=["HS256"])["exp"]


def test_a_note_is_narrowed_to_what_this_service_models(api: DulyAPI):
    notes = api.get_notes(USER_JWT)

    # The API also sends last_updated and last_author_type, and strings for the
    # id and timestamps, so the payload can't be splatted into Note.
    assert len(notes) == 1
    assert str(notes[0].id) == NOTE_RESPONSE["id"]
    assert notes[0].title == "Groceries"
    assert notes[0].created_at.year == 2026
