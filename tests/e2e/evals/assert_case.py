from anthropic import Anthropic

from tests.e2e.evals.eval_case import EvalCase
from tests.e2e.evals.failures import failures
from tests.e2e.evals.runner import run_case


def assert_case(case: EvalCase, client: Anthropic) -> None:
    outcome = run_case(case, client)

    unmet = failures(case, outcome)

    assert not unmet, (
        f"{case.name} did not meet: {', '.join(unmet)}\n" f"answered: {outcome.answer}"
    )
