import asyncio
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Message, MessageRole

CONTEXT_WINDOW_SIZE: int = 12


@dataclass(frozen=True)
class CachedMessage:
    message_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime


class ContextWindowCache:
    """Keeps the most recent messages of each session in memory.

    The first read for a session loads its newest messages from the database.
    Every later read is served from memory until the session is ended or
    deleted.

    Two messages are kept beyond ``CONTEXT_WINDOW_SIZE``: the message currently
    being answered (which is excluded from the returned window) and one message
    that turn alignment may need to pull in. The window handed to the LLM
    therefore never exceeds ``CONTEXT_WINDOW_SIZE`` plus one alignment message.
    """

    def __init__(self, max_size: int = CONTEXT_WINDOW_SIZE) -> None:
        self._max_size: int = max_size
        self._windows: dict[uuid.UUID, deque[CachedMessage]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_messages(
            self,
            session_id: uuid.UUID,
            db_session: AsyncSession,
            exclude_message_id: uuid.UUID | None = None,
    ) -> list[CachedMessage]:
        """Return the conversation history in chronological order, oldest first.

        ``exclude_message_id`` keeps the message currently being answered out of
        its own context window. The recording endpoint always excludes the
        newest message, so the oldest returned message is a user message
        whenever a newer one exists.
        """
        async with self._lock:
            window = self._windows.get(session_id)
            if window is None:
                window = await self._load_from_database(session_id, db_session)
                self._windows[session_id] = window

            history: list[CachedMessage] = [
                cached
                for cached in window
                if cached.message_id != exclude_message_id
            ]
            return self._turn_aligned_tail(history)

    async def append(
            self,
            session_id: uuid.UUID,
            message: CachedMessage,
    ) -> None:
        """Add a committed message to the window.

        If the session is not cached yet, do nothing: the next read loads the
        window from the database, which already contains this message.
        Appending a message that is already cached is a no-op, so a retried
        request cannot spend a second slot on the same message.
        """
        async with self._lock:
            window = self._windows.get(session_id)
            if window is None:
                return

            if any(cached.message_id == message.message_id for cached in window):
                return

            window.append(message)
            self._sort_chronologically(window)
            self._trim(window)

    async def clear(self, session_id: uuid.UUID) -> None:
        """Forget a session's window so it does not leak after the session ends."""
        async with self._lock:
            self._windows.pop(session_id, None)

    async def _load_from_database(
            self,
            session_id: uuid.UUID,
            db_session: AsyncSession,
    ) -> deque[CachedMessage]:
        result = await db_session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(self._max_size + 2)
        )
        messages: list[Message] = list(result.scalars().all())

        # The query returns newest first; the prompt needs oldest first.
        messages.reverse()

        window: deque[CachedMessage] = deque(
            (
                CachedMessage(
                    message_id=message.id,
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                )
                for message in messages
            ),
            maxlen=self._max_size + 2,
        )
        self._trim(window)
        return window

    def _turn_aligned_tail(self, history: list[CachedMessage]) -> list[CachedMessage]:
        """Return the newest history, widened by one message when needed.

        If the oldest message in the requested tail is an assistant reply, the
        user message it answers is pulled in as well. That is one extra message,
        not a whole extra turn.
        """
        start: int = max(0, len(history) - self._max_size)
        if start > 0 and history[start].role is MessageRole.ASSISTANT:
            start -= 1
        return history[start:]

    def _trim(self, window: deque[CachedMessage]) -> None:
        """Drop the oldest messages, then any reply whose question fell outside."""
        while len(window) > self._max_size + 2:
            window.popleft()
        while window and window[0].role is MessageRole.ASSISTANT:
            window.popleft()

    @staticmethod
    def _sort_chronologically(window: deque[CachedMessage]) -> None:
        """Keep order stable when concurrent requests append out of order.

        Ties break on ``message_id`` so an in-memory window orders exactly like
        a database reload, which sorts on ``(created_at, id)``.
        """
        ordered: list[CachedMessage] = sorted(
            window,
            key=lambda cached: (cached.created_at, cached.message_id),
        )
        window.clear()
        window.extend(ordered)


context_window_cache: ContextWindowCache = ContextWindowCache()
