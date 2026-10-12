from typing import Any

from src.chatbot.tools.notes_tool import NotesTool
from src.chatbot.tools.rendering import as_limit, render_notes


class SearchNotes(NotesTool):
    name = "search_notes"
    description = (
        "Find the user's notes matching a keyword, searching titles and "
        "content. Matching is literal, so it will not find synonyms or "
        "paraphrases: try the words the user would have written down."
    )
    error_response = (
        "Could not reach the notes service, so the notes could not be searched."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The keyword to look for.",
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
            return "No query given. Provide a keyword to search for."

        notes = self._api.get_notes_by_keyword(self.jwt, query)

        return render_notes(notes, as_limit(tool_input.get("limit")))
