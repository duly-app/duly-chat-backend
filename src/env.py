import os
from abc import ABC, abstractmethod
from typing import Final

ANTHROPIC_API_KEY: Final = "ANTHROPIC_API_KEY"
SIGNING_KEY: Final = "SIGNING_KEY"
SERVICE_KEY: Final = "SERVICE_KEY"
DULY_SERVICE_URI: Final = "DULY_SERVICE_URI"
LOG_LEVEL: Final = "LOG_LEVEL"

REQUIRED: Final = (ANTHROPIC_API_KEY, SIGNING_KEY, SERVICE_KEY)
DEFAULTS: Final = {
    DULY_SERVICE_URI: "http://localhost:8001",
    LOG_LEVEL: "INFO",
}
KNOWN: Final = (*REQUIRED, *DEFAULTS)


class EnvError(RuntimeError):
    """The environment can't support the service."""


class Env(ABC):
    @abstractmethod
    def get(self, name: str) -> str | None:
        raise NotImplementedError

    def __getitem__(self, name: str) -> str:
        value = self.get(name) or DEFAULTS.get(name)

        if value is None:
            raise EnvError(f"{name} is not set")

        return value

    def validate(self) -> None:
        missing = [name for name in REQUIRED if not self.get(name)]

        if missing:
            raise EnvError(f"Not set: {', '.join(missing)}")

        if self[SERVICE_KEY] == self[SIGNING_KEY]:
            raise EnvError(
                "SERVICE_KEY must differ from SIGNING_KEY: one signs user "
                "sessions, the other proves the assistant authored a note, "
                "and leaking one must not forge the other"
            )


class OSEnv(Env):
    def get(self, name: str) -> str | None:
        return os.environ.get(name)
