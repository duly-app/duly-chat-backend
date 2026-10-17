from src.env import ANTHROPIC_API_KEY, KNOWN, SERVICE_KEY, SIGNING_KEY, Env

VALID_VALUES = {
    ANTHROPIC_API_KEY: "anthropic-key-not-used-by-any-test",
    SIGNING_KEY: "signing-key-that-is-at-least-32-bytes",
    SERVICE_KEY: "service-key-that-is-at-least-32-bytes",
}


class FakeEnv(Env):
    """An environment held in a dict rather than read from the process."""

    def __init__(self, **overrides: str | None):
        unknown = set(overrides) - set(KNOWN)

        assert not unknown, f"Not environment variables: {sorted(unknown)}"

        self._values = {**VALID_VALUES, **overrides}

    def get(self, name: str) -> str | None:
        return self._values.get(name)
