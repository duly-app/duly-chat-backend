import pytest
from anthropic import Anthropic

from src.chatbot.loop_result import Trajectory
from src.chatbot.tools.create_note import CreateNote
from src.chatbot.tools.delete_note import DeleteNote
from src.chatbot.tools.get_note import GetNote
from src.chatbot.tools.list_notes import ListNotes
from src.chatbot.tools.search_notes import SearchNotes
from src.chatbot.tools.update_note import UpdateNote
from tests.e2e.evals.assert_case import assert_case
from tests.e2e.evals.eval_case import EvalCase
from tests.e2e.evals.outcome.any_tool_result import AnyToolResult
from tests.e2e.evals.outcome.disjunction import AnyOf
from tests.e2e.evals.outcome.keyword_match import KeywordMatch
from tests.e2e.evals.outcome.negation import Not
from tests.e2e.evals.outcome.no_tool_errors import NoToolErrors
from tests.e2e.evals.outcome.outcome import Outcome
from tests.e2e.evals.outcome.toolcall_match import ToolCallMatch
from tests.e2e.evals.outcome.toolresult_match import ToolResultMatch

NOTES_DB = "many_notes"

FLAT_VIEWINGS = "9f1c7a52-3b6e-4f80-9d21-7a4e5c8b1003"
READING_LIST = "9f1c7a52-3b6e-4f80-9d21-7a4e5c8b1004"


def no_writes() -> list[Outcome[Trajectory]]:
    """Nothing in the trajectory changed a note."""
    return [
        Not(ToolCallMatch(CreateNote, {})),
        Not(ToolCallMatch(UpdateNote, {})),
        Not(ToolCallMatch(DeleteNote, {})),
    ]


# Retrieval and grounding


@pytest.mark.evals
def test_answers_from_a_note_body(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="answers_from_a_note_body",
            db=NOTES_DB,
            question=(
                "What tuning am I working in, according to my guitar practice log?"
            ),
            trajectory_outcomes=[NoToolErrors()],
            answer_outcomes=[KeywordMatch(["DADGAD"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_reads_the_full_note_when_the_preview_is_truncated(
    live_anthropic_client: Anthropic,
):
    # The damp sits past PREVIEW_LENGTH, so no list or search preview carries
    # it. Answering means fetching the note in full.
    assert_case(
        EvalCase(
            name="reads_the_full_note_when_the_preview_is_truncated",
            db=NOTES_DB,
            question="What was wrong with the Bos en Lommer flat I looked at?",
            trajectory_outcomes=[
                ToolCallMatch(GetNote, {"note_id": FLAT_VIEWINGS}),
                NoToolErrors(),
            ],
            answer_outcomes=[KeywordMatch(["damp"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_finds_the_most_recently_updated_note(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="finds_the_most_recently_updated_note",
            db=NOTES_DB,
            question="Which of my notes did I change most recently?",
            trajectory_outcomes=[NoToolErrors()],
            answer_outcomes=[KeywordMatch(["guitar practice log"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_filters_notes_by_an_absolute_date_range(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="filters_notes_by_an_absolute_date_range",
            db=NOTES_DB,
            question="Which of my notes did I update in September 2026?",
            available_tools=[ListNotes],
            trajectory_outcomes=[ToolCallMatch(ListNotes, {}), NoToolErrors()],
            answer_outcomes=[KeywordMatch(["sourdough"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_counts_all_the_notes_not_just_the_page(live_anthropic_client: Anthropic):
    # Twelve notes, and list_notes pages at ten, so the count is only right if
    # it reads the header.
    assert_case(
        EvalCase(
            name="counts_all_the_notes_not_just_the_page",
            db=NOTES_DB,
            question="How many notes do I have in total?",
            trajectory_outcomes=[NoToolErrors(), *no_writes()],
            answer_outcomes=[KeywordMatch(["12"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_picks_the_relevant_notes_out_of_a_long_listing(
    live_anthropic_client: Anthropic,
):
    assert_case(
        EvalCase(
            name="picks_the_relevant_notes_out_of_a_long_listing",
            db=NOTES_DB,
            question="Which of my notes are about cooking?",
            available_tools=[ListNotes],
            trajectory_outcomes=[
                ToolCallMatch(ListNotes, {}),
                AnyToolResult(KeywordMatch(["Sourdough starter"])),
                AnyToolResult(KeywordMatch(["Pasta dough ratios"])),
                NoToolErrors(),
                *no_writes(),
            ],
            answer_outcomes=[
                KeywordMatch(["sourdough", "pasta"]),
                Not(KeywordMatch(["dutch vocabulary"])),
            ],
        ),
        live_anthropic_client,
    )


# Carrying an id across steps


@pytest.mark.evals
def test_updates_the_note_it_found(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="updates_the_note_it_found",
            db=NOTES_DB,
            question="Add Dune to my reading list.",
            trajectory_outcomes=[
                ToolCallMatch(UpdateNote, {"note_id": READING_LIST}),
                NoToolErrors(),
            ],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_creates_a_note_it_is_asked_for(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="creates_a_note_it_is_asked_for",
            db=NOTES_DB,
            question=(
                "Make a note called 'Bike maintenance' that says the brake "
                "pads need replacing."
            ),
            trajectory_outcomes=[
                ToolCallMatch(CreateNote, {"title": "Bike maintenance"}),
                NoToolErrors(),
            ],
        ),
        live_anthropic_client,
    )


# Not doing things


@pytest.mark.evals
def test_does_not_invent_a_note_that_does_not_exist(live_anthropic_client: Anthropic):
    # There is no scuba note. Looking and saying so is right; describing one
    # is the failure this catches.
    assert_case(
        EvalCase(
            name="does_not_invent_a_note_that_does_not_exist",
            db=NOTES_DB,
            question="What does my note about scuba diving say?",
            trajectory_outcomes=[
                ToolResultMatch(SearchNotes, KeywordMatch(["No notes found"])),
                NoToolErrors(),
                *no_writes(),
            ],
            answer_outcomes=[
                AnyOf(
                    [
                        KeywordMatch(["no note"]),
                        KeywordMatch(["don't have"]),
                        KeywordMatch(["doesn't have"]),
                        KeywordMatch(["couldn't find"]),
                        KeywordMatch(["could not find"]),
                        KeywordMatch(["nothing about scuba"]),
                        KeywordMatch(["no scuba"]),
                    ]
                )
            ],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_does_not_write_when_only_asked_a_question(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="does_not_write_when_only_asked_a_question",
            db=NOTES_DB,
            question="What are the pasta dough ratios I wrote down?",
            trajectory_outcomes=[NoToolErrors(), *no_writes()],
            answer_outcomes=[KeywordMatch(["100g", "egg"])],
        ),
        live_anthropic_client,
    )


@pytest.mark.evals
def test_does_not_delete_without_confirmation(live_anthropic_client: Anthropic):
    assert_case(
        EvalCase(
            name="does_not_delete_without_confirmation",
            db=NOTES_DB,
            question="Delete my tax return note.",
            trajectory_outcomes=[NoToolErrors(), Not(ToolCallMatch(DeleteNote, {}))],
        ),
        live_anthropic_client,
    )
