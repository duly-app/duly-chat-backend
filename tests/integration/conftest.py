from pathlib import Path
from typing import Callable, TypeAlias

import pytest

from src.adapters.api.api_adapter import APIAdapter
from tests.integration.fakes.fake_api_adapter import FakeAPIAdapter
from tests.integration.fakes.fake_token_service import FakeTokenService
from tests.integration.fixtures.anthropic import (  # noqa: F401
    AnthropicClientFactory,
    anthropic_client,
)
from tests.integration.fixtures.context import context_builder  # noqa: F401
from tests.integration.helpers.note_db import NoteDB

NOTE_DB = Path(__file__).parent / "note_db"

DBName: TypeAlias = str
SecretKey: TypeAlias = str

NoteDBFactory: TypeAlias = Callable[[DBName], NoteDB]
TokenServiceFactory: TypeAlias = Callable[[SecretKey], FakeTokenService]
APIAdapterFactory: TypeAlias = Callable[[DBName, SecretKey], APIAdapter]


def create_note_db(db_name: DBName) -> NoteDB:
    db_path = NOTE_DB / db_name / "notes.json"
    assert db_path.exists(), f"Database file does not exist: {db_path}"

    return NoteDB(db_path)


def create_api_adapter(note_db: NoteDB, token_service: FakeTokenService) -> APIAdapter:
    return FakeAPIAdapter(token_service, note_db)


@pytest.fixture
def note_db() -> NoteDBFactory:
    def _note_db(db_name: DBName) -> NoteDB:
        return create_note_db(db_name)

    return _note_db


@pytest.fixture
def token_service() -> TokenServiceFactory:
    def _token_service(secret_key: SecretKey) -> FakeTokenService:
        return FakeTokenService(secret_key)

    return _token_service


@pytest.fixture
def api_adapter() -> APIAdapterFactory:
    def _api_adapter(db_name: DBName, secret_key: SecretKey) -> APIAdapter:
        note_db = create_note_db(db_name)
        token_service = FakeTokenService(secret_key)

        return create_api_adapter(note_db, token_service)

    return _api_adapter
