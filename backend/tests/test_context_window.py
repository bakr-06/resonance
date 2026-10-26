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

from db.models import Exchange
from services.context_window import ContextWindowCache

MAX_SIZE: int = 6
BASE_TIME: datetime = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
SESSION_ID: uuid.UUID = uuid.UUID(int=999)


class FakeResult:
    """The slice of ``Result`` that ``_load_from_database`` actually uses."""

    def __init__(self, rows: list[Exchange]) -> None:
        self._rows: list[Exchange] = rows

    def scalars(self) -> "FakeResult":
        return self

    def all(self) -> list[Exchange]:
        return self._rows


class FakeSession:
    """Emulates a query result, not a database engine.

    ``rows`` must already be newest-first and one minute apart in age; the
    limit is applied here to mimic the SQL ``LIMIT`` clause.
    """

    def __init__(self, rows: list[Exchange], limit: int = MAX_SIZE) -> None:
        self._rows: list[Exchange] = rows
        self._limit: int = limit
        self.execute_calls: int = 0

    async def execute(self, statement: Any) -> FakeResult:
        self.execute_calls += 1
        return FakeResult(self._rows[: self._limit])


def as_db_session(session: FakeSession) -> AsyncSession:
    """The cache only calls ``execute``; the cast keeps the call sites honest."""
    return cast(AsyncSession, session)


def make_exchange(
        exchange_id: uuid.UUID,
        transcript: str,
        created_at: datetime,
) -> Exchange:
    """Build a detached ORM row, so a renamed column breaks the tests too."""
    return Exchange(
        id=exchange_id,
        session_id=SESSION_ID,
        created_at=created_at,
        transcript=transcript,
        reflection="",
        detected_mode=None,
    )


def make_rows(count: int) -> list[Exchange]:
    """Return ``count`` exchanges, newest first, one minute apart.

    Transcripts read ``entry 1`` (oldest) through ``entry <count>`` (newest).
    """
    return [
        make_exchange(
            exchange_id=uuid.UUID(int=index),
            transcript=f"entry {index}",
            created_at=BASE_TIME + timedelta(minutes=index),
        )
        for index in range(count, 0, -1)
    ]


def make_cache() -> ContextWindowCache:
    """A fresh cache per test: the module-level singleton would leak state."""
    return ContextWindowCache(max_size=MAX_SIZE)


def test_loads_existing_exchanges_oldest_first() -> None:
    """The database returns newest first; the prompt needs oldest first."""
    session = FakeSession(make_rows(3))
    cache = make_cache()

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "entry 2", "entry 3"]


def test_empty_session_returns_empty_list() -> None:
    """A session with no history must not crash or invent entries."""
    session = FakeSession([])
    cache = make_cache()

    assert asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session))) == []


def test_second_read_is_served_from_memory() -> None:
    """A cache that re-queries every time would pass every other test."""
    session = FakeSession(make_rows(3))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert session.execute_calls == 1


def test_append_on_uncached_session_does_not_create_window() -> None:
    """Appending must not populate the cache; the next read loads from the DB."""
    session = FakeSession(make_rows(2))
    cache = make_cache()

    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=777),
            transcript="ghost",
            created_at=BASE_TIME + timedelta(minutes=99),
        )
    )

    assert session.execute_calls == 0

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "entry 2"]
    assert session.execute_calls == 1


def test_clear_forces_reload_from_database() -> None:
    """Ending or deleting a session must drop the window, not keep serving it."""
    session = FakeSession(make_rows(2))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(cache.clear(SESSION_ID))
    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert session.execute_calls == 2


def test_window_is_capped_at_max_size() -> None:
    """Appending a seventh exchange evicts the oldest, not the newest."""
    session = FakeSession(make_rows(MAX_SIZE))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=MAX_SIZE + 1),
            transcript=f"entry {MAX_SIZE + 1}",
            created_at=BASE_TIME + timedelta(minutes=MAX_SIZE + 1),
        )
    )

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert len(transcripts) == MAX_SIZE
    assert "entry 1" not in transcripts
    assert transcripts[-1] == f"entry {MAX_SIZE + 1}"


def test_load_uses_only_the_newest_rows() -> None:
    """The SQL LIMIT, not the deque, is what caps a cold load."""
    session = FakeSession(make_rows(10), limit=MAX_SIZE)
    cache = make_cache()

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == [f"entry {index}" for index in range(5, 11)]


def test_append_sorts_chronologically() -> None:
    """Concurrent requests can append out of order; the window must not care."""
    session = FakeSession(make_rows(1))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=5),
            transcript="five",
            created_at=BASE_TIME + timedelta(minutes=5),
        )
    )
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=3),
            transcript="three",
            created_at=BASE_TIME + timedelta(minutes=3),
        )
    )

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "three", "five"]


def test_duplicate_append_is_ignored() -> None:
    """A retried request must not spend a slot on the same exchange twice."""
    session = FakeSession(make_rows(1))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    for _ in range(2):
        asyncio.run(
            cache.append(
                session_id=SESSION_ID,
                exchange_id=uuid.UUID(int=50),
                transcript="hello",
                created_at=BASE_TIME + timedelta(minutes=50),
            )
        )

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "hello"]


def test_equal_timestamps_break_ties_by_id() -> None:
    """Memory must order ties the way a database reload would.

    ``_load_from_database`` orders by ``created_at ASC, id ASC`` once reversed,
    so an in-memory window that sorts on ``created_at`` alone can disagree with
    the same session after a restart.
    """
    session = FakeSession(make_rows(1))
    cache = make_cache()
    same_time = BASE_TIME + timedelta(minutes=50)

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=20),
            transcript="twenty",
            created_at=same_time,
        )
    )
    asyncio.run(
        cache.append(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=10),
            transcript="ten",
            created_at=same_time,
        )
    )

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "ten", "twenty"]


def test_update_transcript_replaces_in_place() -> None:
    """Editing an exchange must not move it or duplicate it."""
    session = FakeSession(make_rows(3))
    cache = make_cache()

    asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))
    asyncio.run(
        cache.update_transcript(
            session_id=SESSION_ID,
            exchange_id=uuid.UUID(int=2),
            transcript="edited",
        )
    )

    transcripts = asyncio.run(cache.get_transcripts(SESSION_ID, as_db_session(session)))

    assert transcripts == ["entry 1", "edited", "entry 3"]


def test_exclude_exchange_id_removes_exactly_one() -> None:
    """An edited exchange must not appear as its own context."""
    session = FakeSession(make_rows(3))
    cache = make_cache()

    transcripts = asyncio.run(
        cache.get_transcripts(
            SESSION_ID,
            as_db_session(session),
            exclude_exchange_id=uuid.UUID(int=2),
        )
    )

    assert transcripts == ["entry 1", "entry 3"]
