"""Tests for ``services.ai_analysis`` prompt logging and model calls.

These do not need Ollama: ``httpx.MockTransport`` stands in for the server, so
the request body and the log lines can be checked together. Run from
``backend/`` with ``python -m pytest -q``.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from db.models import MessageRole
from logging_config import PROMPT_LOGGER_NAME
from services.ai_analysis import (
    AnalysisResult,
    _build_messages,
    _chat,
    _log_messages,
    _max_chars,
    analyze,
)
from services.context_window import CachedMessage

LOGGER_NAME: str = "services.ai_analysis"
SESSION_ID: uuid.UUID = uuid.UUID(int=42)

SYSTEM_MESSAGE: str = "you are a test assistant, reply briefly"
USER_MESSAGE: str = "Earlier entry 1:\nyesterday"


def test_prompt_dump_contains_the_full_text(caplog: pytest.LogCaptureFixture) -> None:
    """The point of the dump is the verbatim text, not a summary of it."""
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_MESSAGE},
    ]

    with caplog.at_level(logging.DEBUG, logger=PROMPT_LOGGER_NAME):
        _log_messages(messages, SESSION_ID)

    assert SYSTEM_MESSAGE in caplog.text
    assert USER_MESSAGE in caplog.text
    assert "role=system" in caplog.text
    assert getattr(caplog.records[0], "session_id") == str(SESSION_ID)


def test_chat_sends_num_ctx_and_logs_token_counts(
        caplog: pytest.LogCaptureFixture,
) -> None:
    """The request must carry num_ctx, and the response tokens must be logged."""
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "{}"},
                "prompt_eval_count": 321,
                "eval_count": 42,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    async def call() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
                await _chat(
                    http_client=client,
                    base_url="http://ollama.test",
                    model="llama3.1",
                    num_ctx=8192,
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": USER_MESSAGE},
                    ],
                    temperature=0.4,
                    force_json=True,
                    purpose="analysis",
                    session_id=SESSION_ID,
                )

    asyncio.run(call())

    assert bodies[0]["options"]["num_ctx"] == 8192
    assert bodies[0]["format"] == "json"
    assert "purpose=analysis" in caplog.text
    assert "chars=" in caplog.text
    assert "prompt_tokens=321" in caplog.text
    assert "completion_tokens=42" in caplog.text
    assert all(
        getattr(record, "session_id", None) == str(SESSION_ID)
        for record in caplog.records
    )


def test_analyze_sends_role_tagged_history() -> None:
    """The prompt is a real chat message list: system, history, current user."""
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "That sounds heavy."},
                "prompt_eval_count": 812,
                "eval_count": 21,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    async def call() -> AnalysisResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await analyze(
                message="I feel guilty",
                context=[
                    CachedMessage(
                        message_id=uuid.uuid4(),
                        role=MessageRole.USER,
                        content="I skipped class again.",
                        created_at=datetime.now(timezone.utc),
                    ),
                    CachedMessage(
                        message_id=uuid.uuid4(),
                        role=MessageRole.ASSISTANT,
                        content="You mentioned that last week.",
                        created_at=datetime.now(timezone.utc),
                    ),
                ],
                http_client=client,
                base_url="http://ollama.test",
                model="llama3.1",
                num_ctx=8192,
                session_id=SESSION_ID,
                system_prompt=SYSTEM_MESSAGE,
            )

    result: AnalysisResult = asyncio.run(call())

    messages = bodies[0]["messages"]
    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[1]["content"] == "I skipped class again."
    assert messages[2]["content"] == "You mentioned that last week."
    assert messages[3]["content"] == "I feel guilty"
    assert "Earlier entry" not in json.dumps(bodies[0])
    assert "format" not in bodies[0]
    assert result["content"] == "That sounds heavy."


def make_cached(role: MessageRole, content: str) -> CachedMessage:
    return CachedMessage(
        message_id=uuid.uuid4(),
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )


def test_build_messages_keeps_a_contiguous_history_suffix() -> None:
    """Dropping a message must drop everything older, not just that one."""
    history: list[CachedMessage] = [
        make_cached(MessageRole.USER, "x" * 500),
        make_cached(MessageRole.USER, "middle"),
        make_cached(MessageRole.ASSISTANT, "newest"),
    ]

    messages = _build_messages(None, history, "current", num_ctx=1100)

    assert [message["content"] for message in messages] == [
        "middle",
        "newest",
        "current",
    ]
    assert [message["role"] for message in messages] == ["user", "assistant", "user"]


def test_build_messages_does_not_skip_a_newest_message_that_does_not_fit() -> None:
    """A too-large newest message must not let an older message jump the queue."""
    history: list[CachedMessage] = [
        make_cached(MessageRole.USER, "old small"),
        make_cached(MessageRole.USER, "x" * 500),
    ]

    messages = _build_messages(None, history, "current", num_ctx=1100)

    assert [message["content"] for message in messages] == ["current"]


def test_build_messages_always_includes_the_current_message() -> None:
    """The recording being analyzed must survive even when it fills the budget."""
    messages = _build_messages(None, [], "x" * 1000, num_ctx=1100)

    assert [message["role"] for message in messages] == ["user"]
    assert messages[-1]["content"]
    assert len(messages[-1]["content"]) == _max_chars(1100)


def test_build_messages_reserves_space_for_the_system_prompt() -> None:
    """System prompt plus current message must stay inside the character budget."""
    num_ctx: int = 1100
    system_prompt: str = "s" * 100

    messages = _build_messages(
        system_prompt,
        [make_cached(MessageRole.USER, "old history")],
        "c" * 1000,
        num_ctx=num_ctx,
    )

    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == system_prompt
    assert messages[-1]["role"] == "user"
    assert sum(len(message["content"]) for message in messages) <= _max_chars(num_ctx)
    assert all(message["content"] != "old history" for message in messages)
