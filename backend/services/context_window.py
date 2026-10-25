import asyncio
import uuid
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Exchange

CONTEXT_WINDOW_SIZE: int = 6


@dataclass(frozen=True)
class CachedExchange:
    exchange_id: uuid.UUID
    transcript: str
    created_at: datetime


class ContextWindowCache:
    """Keeps the most recent exchanges of each session in memory.

    The first read for a session loads its last ``CONTEXT_WINDOW_SIZE``
    exchanges from the database. Every later read is served from memory until
    the session is ended or deleted.
    """

    def __init__(self, max_size: int = CONTEXT_WINDOW_SIZE) -> None:
        self._max_size: int = max_size
        self._windows: dict[uuid.UUID, deque[CachedExchange]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_transcripts(
            self,
            session_id: uuid.UUID,
            db_session: AsyncSession,
            exclude_exchange_id: uuid.UUID | None = None,
    ) -> list[str]:
        """Return the window in chronological order, oldest first.

        ``exclude_exchange_id`` keeps the exchange currently being analyzed out
        of its own context window.
        """
        async with self._lock:
            window = self._windows.get(session_id)
            if window is None:
                window = await self._load_from_database(session_id, db_session)
                self._windows[session_id] = window

            return [
                cached.transcript
                for cached in window
                if cached.exchange_id != exclude_exchange_id
            ]

    async def append(
            self,
            session_id: uuid.UUID,
            exchange_id: uuid.UUID,
            transcript: str,
            created_at: datetime,
    ) -> None:
        """Add a committed exchange to the window.

        If the session is not cached yet, do nothing: the next read loads the
        window from the database, which already contains this exchange.
        """
        async with self._lock:
            window = self._windows.get(session_id)
            if window is None:
                return

            window.append(
                CachedExchange(
                    exchange_id=exchange_id,
                    transcript=transcript,
                    created_at=created_at,
                )
            )
            self._sort_chronologically(window)

    async def update_transcript(
            self,
            session_id: uuid.UUID,
            exchange_id: uuid.UUID,
            transcript: str,
    ) -> None:
        """Replace the cached transcript after an exchange is edited."""
        async with self._lock:
            window = self._windows.get(session_id)
            if window is None:
                return

            for index, cached in enumerate(window):
                if cached.exchange_id == exchange_id:
                    window[index] = replace(cached, transcript=transcript)
                    return

    async def clear(self, session_id: uuid.UUID) -> None:
        """Forget a session's window so it does not leak after the session ends."""
        async with self._lock:
            self._windows.pop(session_id, None)

    async def _load_from_database(
            self,
            session_id: uuid.UUID,
            db_session: AsyncSession,
    ) -> deque[CachedExchange]:
        result = await db_session.execute(
            select(Exchange)
            .where(Exchange.session_id == session_id)
            .order_by(Exchange.created_at.desc(), Exchange.id.desc())
            .limit(self._max_size)
        )
        exchanges: list[Exchange] = list(result.scalars().all())

        # The query returns newest first; the prompt needs oldest first.
        exchanges.reverse()

        return deque(
            (
                CachedExchange(
                    exchange_id=exchange.id,
                    transcript=exchange.transcript,
                    created_at=exchange.created_at,
                )
                for exchange in exchanges
            ),
            maxlen=self._max_size,
        )

    @staticmethod
    def _sort_chronologically(window: deque[CachedExchange]) -> None:
        """Keep order stable when concurrent requests append out of order."""
        ordered: list[CachedExchange] = sorted(
            window,
            key=lambda cached: cached.created_at,
        )
        window.clear()
        window.extend(ordered)


context_window_cache: ContextWindowCache = ContextWindowCache()
