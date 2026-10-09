from datetime import timedelta
from uuid import uuid4

import pytest
from anthropic.types import MessageParam

from src.chatbot.threads.thread_store import Thread, ThreadStore, record_turn

THREAD_ID = uuid4()


def message(text: str) -> MessageParam:
    return {"role": "user", "content": text}


def test_a_new_thread_starts_empty_and_is_not_stored():
    store = ThreadStore()
    user_id = uuid4()

    thread = store.load(user_id, THREAD_ID)

    assert thread.messages == []

    assert len(store) == 0


def test_saved_messages_come_back_on_the_next_load():
    store = ThreadStore()
    user_id = uuid4()

    thread = store.load(user_id, THREAD_ID)
    thread.extend([message("first")])
    store.save(thread)

    assert store.load(user_id, THREAD_ID).messages == [message("first")]
    assert (user_id, THREAD_ID) in store


def test_a_loaded_thread_is_a_copy():
    store = ThreadStore()
    user_id = uuid4()

    store.save(Thread(user_id, THREAD_ID, [message("first")]))

    stray = store.load(user_id, THREAD_ID)
    stray.extend([message("never saved")])

    assert store.load(user_id, THREAD_ID).messages == [message("first")]


def test_threads_are_scoped_to_their_user():
    store = ThreadStore()
    owner, stranger = uuid4(), uuid4()

    store.save(Thread(owner, THREAD_ID, [message("private")]))

    assert store.load(stranger, THREAD_ID).messages == []
    assert store[stranger] == {}
    assert (stranger, THREAD_ID) not in store


def test_the_longest_unused_thread_is_dropped_over_the_cap():
    store = ThreadStore(max_threads_per_user=2)
    user_id = uuid4()
    a, b, c = uuid4(), uuid4(), uuid4()

    for thread_id in (a, b):
        store.save(Thread(user_id, thread_id))

    # Touching a makes b the longest unused, so b goes and a survives —
    # eviction follows last use, not the order threads were created in.
    store.save(store.load(user_id, a))
    store.save(Thread(user_id, c))

    assert set(store[user_id]) == {a, c}


def test_expired_threads_are_dropped_on_access():
    store = ThreadStore(ttl=timedelta(0))
    user_id = uuid4()

    store.save(Thread(user_id, THREAD_ID, [message("stale")]))

    # Expiry is lazy, so the thread is still held until something touches it.
    assert store.load(user_id, THREAD_ID).messages == []
    assert len(store) == 0


def test_record_turn_saves_what_the_turn_added():
    store = ThreadStore()
    user_id = uuid4()

    with record_turn(store, user_id, THREAD_ID) as thread:
        thread.extend([message("first")])

    assert store.load(user_id, THREAD_ID).messages == [message("first")]


def test_record_turn_keeps_history_when_the_turn_fails():
    store = ThreadStore()
    user_id = uuid4()

    class Boom(Exception):
        """Local so that only this test's own raise can satisfy the assertion."""

    with pytest.raises(Boom):
        with record_turn(store, user_id, THREAD_ID) as thread:
            thread.extend([message("said before failing")])
            raise Boom()

    assert store.load(user_id, THREAD_ID).messages == [message("said before failing")]
