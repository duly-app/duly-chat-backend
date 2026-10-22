from src.adapters.api.errors import EmbeddingSearchUnavailable
from src.domain.notes import Note
from src.domain.user import Token
from tests.fakes.fake_api_adapter import FakeAPIAdapter


class UnavailableEmbeddingSearch(FakeAPIAdapter):
    """A notes service that works, except that it cannot embed."""

    def get_notes_by_query_embedding(self, token: Token, query: str) -> list[Note]:
        raise EmbeddingSearchUnavailable(query)
