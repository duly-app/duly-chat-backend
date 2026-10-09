import pytest

from src.env import (
    ANTHROPIC_API_KEY,
    DULY_SERVICE_URI,
    SIGNING_KEY,
    EnvError,
)
from tests.integration.fakes.fake_env import FakeEnv


def test_a_complete_environment_validates():
    FakeEnv().validate()


def test_every_missing_variable_is_reported_at_once():
    env = FakeEnv(SIGNING_KEY=None, ANTHROPIC_API_KEY=None)

    # One restart should tell you everything that's wrong, not the first thing.
    with pytest.raises(EnvError) as error:
        env.validate()

    assert SIGNING_KEY in str(error.value)
    assert ANTHROPIC_API_KEY in str(error.value)


def test_the_service_key_may_not_equal_the_signing_key():
    env = FakeEnv(SERVICE_KEY="same-key", SIGNING_KEY="same-key")

    with pytest.raises(EnvError, match="must differ"):
        env.validate()


def test_an_optional_variable_falls_back_to_its_default():
    assert FakeEnv()[DULY_SERVICE_URI] == "http://localhost:8001"


def test_reading_an_unset_variable_without_a_default_fails_loudly():
    with pytest.raises(EnvError, match=SIGNING_KEY):
        FakeEnv(SIGNING_KEY=None)[SIGNING_KEY]


def test_the_fake_rejects_a_name_that_is_not_an_environment_variable():
    with pytest.raises(AssertionError, match="SIGNING_KEYY"):
        FakeEnv(SIGNING_KEYY=None)
