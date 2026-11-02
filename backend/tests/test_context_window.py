"""Tests for the in-memory sliding context window.

Run from ``backend/`` with ``python -m pytest -q``. Not bare ``pytest``: that
inserts ``tests/`` into ``sys.path`` instead of ``backend/``, and the
``services.context_window`` import fails.

These tests never touch Postgres. ``FakeSession`` stands in for the database
and reproduces the two guarantees ``_load_from_database`` relies on:

1. Rows come back *newest first*, because the cache reverses them.
2. Returns at most ``LIMIT`` rows, because the cap is done in SQL, not here.

If either is dropped from the fake, the tests still pass while asserting the
wrong contract.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Message, MessageRole
from services.context_window import CachedMessage, ContextWindowCache

MAX_SIZE: int = 12
LOAD_LIMIT: int = MAX_SIZE + 2
BASE_TIME: datetime = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
SESSION_ID: uuid.UUID = uuid.UUID(int=999)


class FakeResult:
    """The slice of ``Result`` that ``_load_from_database`` actually uses."""

    def __init__(self, rows: list[Message]) -> None:
        self._rows: list[Message] = rows

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[Message]:
        return self._rows


class FakeSession:
    """Emulates a query result, not a database engine.

    ``rows`` must already be newest-first; the limit is applied here to mimic
    the SQL ``LIMIT`` clause.
    """

    def __init__(self, rows: list[Message], limit: int = LOAD_LIMIT) -> None:
        self._rows: list[Message] = rows
        self._limit: int = limit
        self.execute_calls: int = 0

    async def execute(self, statement: Any) -> FakeResult:
        self.execute_calls += 1
        return FakeResult(self._rows[: self._limit])


def as_db_session(session: FakeSession) -> AsyncSession:
    """The cache only calls ``execute``; the cast keeps the call sites honest."""
    return cast(AsyncSession, session)


def make_message(
        message_id: int,
        role: MessageRole,
        content: str,
        created_at: datetime,
) -> Message:
    """Build a detached ORM row, so a renamed column breaks the tests too."""
    return Message(
        id=uuid.UUID(int=message_id),
        session_id=SESSION_ID,
        role=role,
        content=content,
        created_at=created_at,
    )


def make_cached(
        message_id: int,
        role: MessageRole,
        content: str,
        created_at: datetime,
) -> CachedMessage:
    """Build the in-memory shape the cache stores and appends."""
    return CachedMessage(
        message_id=uuid.UUID(int=message_id),
        role=role,
        content=content,
        created_at=created_at,
    )


def make_turns(turn_count: int) -> list[Message]:
    """Return ``turn_count`` user+reply turns, newest first.

    Messages read ``entry N`` / ``response N``. Each reply is one second after
    its user message, like the real recording flow.
    """
    rows: list[Message] = []
    for turn in range(turn_count, 0, -1):
        rows.append(
            make_message(
                message_id=turn * 2,
                role=MessageRole.ASSISTANT,
                content=f"response {turn}",
                created_at=BASE_TIME + timedelta(minutes=turn, seconds=1),
            )
        )
        rows.append(
            make_message(
                message_id=turn * 2 - 1,
                role=MessageRole.USER,
                content=f"entry {turn}",
                created_at=BASE_TIME + timedelta(minutes=turn),
            )
        )
    return rows


def make_cache() -> ContextWindowCache:
    """A fresh cache per test: the module-level singleton would leak state."""
    return ContextWindowCache(max_size=MAX_SIZE)


def contents(cache: ContextWindowCache, session: FakeSession) -> list[str]:
    messages = asyncio.run(cache.get_messages(SESSION_ID, as_db_session(session)))
    return [message.content for message in messages]


def test_loads_existing_messages_oldest_first() -> None:
    """The database returns newest first; the prompt needs oldest first."""
    session = FakeSession(make_turns(3))
    cache = make_cache()

    assert contents(cache, session) == [
        "entry 1",
        "response 1",
        "entry 2",
        "response 2",
        "entry 3",
        "response 3",
    ]


def test_empty_session_returns_empty_list() -> None:
    """A session with no history must not crash or invent messages."""
    session = FakeSession([])
    cache = make_cache()

    assert contents(cache, session) == []


def test_second_read_is_served_from_memory() -> None:
    """A cache that re-queries every time would pass every other test."""
    session = FakeSession(make_turns(3))
    cache = make_cache()

    contents(cache, session)
    contents(cache, session)

    assert session.execute_calls == 1


def test_append_on_uncached_session_does_not_create_window() -> None:
    """Appending must not populate the cache; the next read loads from the DB."""
    session = FakeSession(make_turns(1))
    cache = make_cache()

    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=77,
                role=MessageRole.USER,
                content="ghost",
                created_at=BASE_TIME + timedelta(minutes=99),
            ),
        )
    )

    assert session.execute_calls == 0
    assert contents(cache, session) == ["entry 1", "response 1"]
    assert session.execute_calls == 1


def test_clear_forces_reload_from_database() -> None:
    """Ending or deleting a session must drop the window, not keep serving it."""
    session = FakeSession(make_turns(2))
    cache = make_cache()

    contents(cache, session)
    asyncio.run(cache.clear(SESSION_ID))
    contents(cache, session)

    assert session.execute_calls == 2


def test_window_is_capped_at_max_size() -> None:
    """Appending a seventh turn evicts the oldest turn, not the newest."""
    session = FakeSession(make_turns(6))
    cache = make_cache()

    contents(cache, session)
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=13,
                role=MessageRole.USER,
                content="entry 7",
                created_at=BASE_TIME + timedelta(minutes=7),
            ),
        )
    )
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=14,
                role=MessageRole.ASSISTANT,
                content="response 7",
                created_at=BASE_TIME + timedelta(minutes=7, seconds=1),
            ),
        )
    )

    window = contents(cache, session)

    assert len(window) == MAX_SIZE
    assert window[0] == "entry 2"
    assert window[-1] == "response 7"


def test_load_uses_only_the_newest_rows() -> None:
    """The SQL LIMIT, not the deque, is what caps a cold load."""
    session = FakeSession(make_turns(10), limit=LOAD_LIMIT)
    cache = make_cache()

    window = contents(cache, session)

    assert window[0] == "entry 5"
    assert window[-1] == "response 10"
    assert len(window) == MAX_SIZE


def test_turn_alignment_pulls_the_question_back_in() -> None:
    """History must not begin with a reply whose question fell outside the window."""
    rows: list[Message] = []
    for turn in range(6, 0, -1):
        rows.append(
            make_message(
                message_id=turn * 2,
                role=MessageRole.ASSISTANT,
                content=f"response {turn}",
                created_at=BASE_TIME + timedelta(minutes=turn, seconds=1),
            )
        )
        rows.append(
            make_message(
                message_id=turn * 2 - 1,
                role=MessageRole.USER,
                content=f"entry {turn}",
                created_at=BASE_TIME + timedelta(minutes=turn),
            )
        )
    rows.insert(
        0,
        make_message(
            message_id=13,
            role=MessageRole.USER,
            content="entry 7",
            created_at=BASE_TIME + timedelta(minutes=7),
        ),
    )

    window = asyncio.run(make_cache().get_messages(SESSION_ID, as_db_session(FakeSession(rows))))

    # The newest twelve start at "response 1"; "entry 1" is pulled back in.
    assert len(window) == MAX_SIZE + 1
    assert window[0].content == "entry 1"
    assert window[0].role is MessageRole.USER


def test_unanswered_user_message_is_kept() -> None:
    """A user message with no reply is real history, not an incomplete turn."""
    session = FakeSession(make_turns(1))
    cache = make_cache()

    contents(cache, session)
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=99,
                role=MessageRole.USER,
                content="entry 2",
                created_at=BASE_TIME + timedelta(minutes=2),
            ),
        )
    )

    assert contents(cache, session)[-1] == "entry 2"


def test_append_sorts_chronologically() -> None:
    """Concurrent requests can append out of order; the window must not care."""
    session = FakeSession(make_turns(1))
    cache = make_cache()

    contents(cache, session)
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=5,
                role=MessageRole.USER,
                content="five",
                created_at=BASE_TIME + timedelta(minutes=5),
            ),
        )
    )
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=3,
                role=MessageRole.USER,
                content="three",
                created_at=BASE_TIME + timedelta(minutes=3),
            ),
        )
    )

    assert contents(cache, session) == ["entry 1", "response 1", "three", "five"]


def test_duplicate_append_is_ignored() -> None:
    """A retried request must not spend a slot on the same message twice."""
    session = FakeSession(make_turns(1))
    cache = make_cache()

    contents(cache, session)
    for _ in range(2):
        asyncio.run(
            cache.append(
                session_id=SESSION_ID,
                message=make_cached(
                    message_id=50,
                    role=MessageRole.USER,
                    content="hello",
                    created_at=BASE_TIME + timedelta(minutes=50),
                ),
            )
        )

    assert contents(cache, session) == ["entry 1", "response 1", "hello"]


def test_equal_timestamps_break_ties_by_id() -> None:
    """Memory must order ties the way a database reload would.

    ``_load_from_database`` orders by ``(created_at DESC, id DESC)``, so an
    in-memory window that sorts on ``created_at`` alone can disagree with the
    same session after a restart.
    """
    session = FakeSession(make_turns(1))
    cache = make_cache()
    same_time = BASE_TIME + timedelta(minutes=50)

    contents(cache, session)
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=20,
                role=MessageRole.USER,
                content="twenty",
                created_at=same_time,
            ),
        )
    )
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            message=make_cached(
                message_id=10,
                role=MessageRole.USER,
                content="ten",
                created_at=same_time,
            ),
        )
    )

    assert contents(cache, session) == ["entry 1", "response 1", "ten", "twenty"]


def test_exclude_message_id_removes_exactly_one() -> None:
    """A message being answered must not appear as its own context."""
    session = FakeSession(make_turns(3))
    cache = make_cache()

    messages = asyncio.run(
        cache.get_messages(
            SESSION_ID,
            as_db_session(session),
            exclude_message_id=uuid.UUID(int=4),
        )
    )

    assert [message.content for message in messages] == [
        "entry 1",
        "response 1",
        "entry 2",
        "entry 3",
        "response 3",
    ]
