from typing import Any

from src.adapters.api.errors import EmbeddingSearchUnavailable
from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.rendering import as_limit, render_notes


class EmbeddingQASearch(NotesTool):
    name = "query_embedding_search"
    description = (
        "Find the user's notes by meaning rather than by wording, using "
        "embeddings. Use it when the user asks a question or describes what "
        "they are looking for in their own words, which may share no words "
        "with the note itself. Phrase the query as the question or "
        "description, not as keywords. Results are ranked, not filtered: the "
        "closest match comes first and relevance falls off down the list, so "
        "the later ones may have nothing to do with the query. Use the ones "
        "that answer it and ignore the rest rather than reporting everything "
        "returned. A note written moments ago may not be searchable yet; "
        "search_notes finds it immediately."
    )
    error_response = (
        "Could not reach the notes service, so the notes could not be searched."
    )
    unavailable_response = (
        "Semantic search is unavailable right now. The notes themselves are "
        "fine: try search_notes with the words the user would have written."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question or description to search for.",
            },
            "limit": {
                "type": "integer",
                "description": "How many notes to return at most. Defaults to 10.",
            },
        },
        "required": ["query"],
    }

    def run(self, **tool_input: Any) -> str:
        query = str(tool_input.get("query", "")).strip()

        if not query:
            return "No query given. Describe what to look for."

        try:
            notes = self._api.get_notes_by_query_embedding(self.jwt, query)
        except EmbeddingSearchUnavailable:
            # Named separately from error_response: the notes are reachable,
            # only the embedder is not, and the model can route around that.
            return self.unavailable_response

        return render_notes(notes, as_limit(tool_input.get("limit")))
