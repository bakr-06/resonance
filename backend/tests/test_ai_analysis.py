"""Tests for ``services.ai_analysis`` prompt logging and model calls.

These do not need Ollama: ``httpx.MockTransport`` stands in for the server, so
the request body and the log lines can be checked together. Run from
``backend/`` with ``python -m pytest -q``.
"""

import asyncio
import json
import logging
import uuid
from typing import Any

import httpx
import pytest

from logging_config import PROMPT_LOGGER_NAME
from services.ai_analysis import AnalysisResult, _chat, _log_messages, analyze

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


def test_analyze_sends_no_system_prompt_and_stores_raw_text() -> None:
    """The model runs unconstrained: no system role, no JSON mode, raw reply."""
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "llama3.1",
                "message": {"role": "assistant", "content": "  That sounds heavy.  "},
                "prompt_eval_count": 120,
                "eval_count": 9,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    async def call() -> AnalysisResult:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await analyze(
                message="I feel guilty",
                context=["I skipped class again."],
                http_client=client,
                base_url="http://ollama.test",
                model="llama3.1",
                num_ctx=8192,
                session_id=SESSION_ID,
            )

    result: AnalysisResult = asyncio.run(call())

    assert [message["role"] for message in bodies[0]["messages"]] == ["user"]
    assert "format" not in bodies[0]
    assert "Earlier entry 1:" in bodies[0]["messages"][0]["content"]
    assert result["reflection"] == "That sounds heavy."
    assert result["detected_mode"] is None
