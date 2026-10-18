import pytest
from anthropic import Anthropic

from src.chatbot.tools.create_note import CreateNote
from src.chatbot.tools.list_notes import ListNotes
from tests.e2e.evals.eval_case import EvalCase
from tests.e2e.evals.failures import failures
from tests.e2e.evals.outcome.keyword_match import KeywordMatch
from tests.e2e.evals.outcome.no_tool_errors import NoToolErrors
from tests.e2e.evals.outcome.toolcall_match import ToolCallMatch
from tests.e2e.evals.runner import run_case

CASES = [
    EvalCase(
        name="lists_notes_updated_in_a_month",
        question="Which of my notes did I update in September 2026?",
        available_tools=[ListNotes],
        trajectory_outcomes=[ToolCallMatch(ListNotes, {}), NoToolErrors()],
        answer_outcomes=[KeywordMatch(["sourdough"])],
    ),
    EvalCase(
        name="answers_from_a_note_body",
        question="What tuning am I working in, according to my guitar practice log?",
        trajectory_outcomes=[NoToolErrors()],
        answer_outcomes=[KeywordMatch(["DADGAD"])],
    ),
    EvalCase(
        name="creates_a_note_it_is_asked_for",
        question=(
            "Make a note called 'Bike maintenance' that says the brake pads "
            "need replacing. Create it now, do not check with me first."
        ),
        trajectory_outcomes=[
            ToolCallMatch(CreateNote, {"title": "Bike maintenance"}),
            NoToolErrors(),
        ],
    ),
]


@pytest.mark.evals
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_cases(case: EvalCase, live_anthropic_client: Anthropic) -> None:
    outcome = run_case(case, live_anthropic_client)

    unmet = failures(case, outcome)

    assert not unmet, f"unmet: {', '.join(unmet)}\nanswered: {outcome.answer}"
