from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Generator, TypeAlias
from uuid import UUID

from anthropic.types import MessageParam
from cachetools import TTLCache

from src.domain.user import UserID

ThreadID: TypeAlias = UUID

DEFAULT_TTL = timedelta(hours=12)
DEFAULT_MAX_THREADS_PER_USER = 50


@dataclass
class Thread:
    """One conversation: who it belongs to, and what has been said in it."""

    user_id: UserID
    thread_id: ThreadID
    messages: list[MessageParam] = field(default_factory=list)

    def extend(self, messages: list[MessageParam]) -> None:
        self.messages.extend(messages)


class ThreadStore:
    """Conversations held in process memory, one expiring cache per user."""

    _threads: dict[UserID, TTLCache[ThreadID, Thread]]

    def __init__(
        self,
        max_threads_per_user: int = DEFAULT_MAX_THREADS_PER_USER,
        ttl: timedelta = DEFAULT_TTL,
    ):
        self._threads = {}
        self._max_threads_per_user = max_threads_per_user
        self._ttl = ttl

    def load(self, user_id: UserID, thread_id: ThreadID) -> Thread:
        """The conversation so far, or a new empty one.

        Returns a copy, and stores nothing: reading an unknown id can't grow
        the store, and a caller can't mutate history without saving.
        """
        cache = self._threads.get(user_id)
        stored = None if cache is None else cache.get(thread_id)

        if stored is None:
            return Thread(user_id=user_id, thread_id=thread_id)

        return Thread(user_id, thread_id, list(stored.messages))

    def save(self, thread: Thread) -> None:
        self._cache(thread.user_id)[thread.thread_id] = thread

    def _cache(self, user_id: UserID) -> TTLCache[ThreadID, Thread]:
        if user_id not in self._threads:
            cache: TTLCache[ThreadID, Thread] = TTLCache(
                maxsize=self._max_threads_per_user,
                ttl=self._ttl.total_seconds(),
            )
            self._threads[user_id] = cache

        return self._threads[user_id]

    def __getitem__(self, user_id: UserID) -> dict[ThreadID, Thread]:
        return dict(self._threads.get(user_id, {}))

    def __contains__(self, key: tuple[UserID, ThreadID]) -> bool:
        user_id, thread_id = key

        return thread_id in self._threads.get(user_id, {})

    def __len__(self) -> int:
        return sum(len(threads) for threads in self._threads.values())


@contextmanager
def record_turn(
    store: ThreadStore, user_id: UserID, thread_id: ThreadID
) -> Generator[Thread]:
    """Load a conversation, hand it over for one turn, then save what it gained.

    The save runs in a finally: a turn that failed part-way still keeps what
    had already been said, since the model was paid for either way.
    """
    thread = store.load(user_id, thread_id)

    try:
        yield thread
    finally:
        store.save(thread)
