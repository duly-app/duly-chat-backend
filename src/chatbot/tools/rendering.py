"""How notes are shown to the model."""

from src.domain.notes import Note

PREVIEW_LENGTH = 200
DEFAULT_LIMIT = 10
MAX_LIMIT = 50


def as_limit(value: object, default: int = DEFAULT_LIMIT) -> int:
    """Coerce a model-supplied limit."""
    try:
        limit = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default

    return max(1, min(limit, MAX_LIMIT))


def render_notes(notes: list[Note], limit: int) -> str:
    """A bounded list of previews, each carrying the id needed to act on it."""
    if not notes:
        return "No notes found."

    shown = notes[:limit]
    entries = "\n\n".join(_preview(note) for note in shown)

    if len(notes) > len(shown):
        header = (
            f"Showing {len(shown)} of {len(notes)} notes. "
            "Search for something more specific to find the rest."
        )
    else:
        header = f"{len(shown)} note{'s' if len(shown) != 1 else ''}."

    return f"{header}\n\n{entries}"


def render_note(note: Note) -> str:
    """One note in full, for when a preview isn't enough."""
    return f"# {note.title} (id: {note.id})\n{note.content}"


def _preview(note: Note) -> str:
    content = note.content.strip()

    if len(content) > PREVIEW_LENGTH:
        content = content[:PREVIEW_LENGTH].rstrip() + "…"

    return f"# {note.title} (id: {note.id})\n{content}"
