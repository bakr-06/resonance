"""Tests for the recording endpoint without a database or a live Ollama.

``create_messages`` is called directly with fakes for the database, the context
cache, Whisper, and the LLM. The fakes record the order of side effects, so the
tests can assert the two central promises of the message model:

1. The user message is committed before analysis starts.
2. An empty reply never creates an assistant row.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from fastapi import Request

from db.models import (
    AnalysisMetrics,
    Message,
    MessageRole,
    Session,
    TranscriptionMetrics,
)
from routes import messages as messages_route
from schemas.messages import CreateMessagesResponse
from services import stt
from services.ai_analysis import AnalysisResult
from services.context_window import CachedMessage

LLM_REPLY: str = "That sounds heavy."


class FakeUploadFile:
    filename: str = "voice.wav"
    content_type: str = "audio/wav"

    def __init__(self, content: bytes) -> None:
        self._content: bytes = content

    async def read(self) -> bytes:
        return self._content


class FakeState:
    http_client: object = object()
    ollama_base_url: str = "http://ollama.test"
    ollama_model: str = "llama3.1"
    ollama_num_ctx: int = 8192
    analysis_system_prompt: str = "system prompt"


class FakeApp:
    state: FakeState = FakeState()


class FakeRequest:
    app: FakeApp = FakeApp()


class FakeDbSession:
    """The slice of ``AsyncSession`` the endpoint uses, plus an event log."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session
        self.added: list[Any] = []
        self.events: list[str] = []

    async def get(self, model: type, identity: uuid.UUID) -> Session | None:
        return self.session if model is Session else None

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def commit(self) -> None:
        self.events.append("commit")
        for instance in self.added:
            if isinstance(instance, Message):
                if instance.id is None:
                    instance.id = uuid.uuid4()
                if instance.created_at is None:
                    instance.created_at = datetime.now(timezone.utc)

    async def refresh(self, instance: Any) -> None:
        return None


class FakeContextWindow:
    def __init__(self) -> None:
        self.appended: list[CachedMessage] = []
        self.excluded_message_id: uuid.UUID | None = None

    async def append(self, session_id: uuid.UUID, message: CachedMessage) -> None:
        self.appended.append(message)

    async def get_messages(
            self,
            session_id: uuid.UUID,
            db_session: Any,
            exclude_message_id: uuid.UUID | None = None,
    ) -> list[CachedMessage]:
        self.excluded_message_id = exclude_message_id
        return []


def make_session() -> Session:
    return Session(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        is_active=True,
    )


def transcribe_result(text: str) -> stt.TranscribeResult:
    return stt.TranscribeResult(
        raw_text=text,
        detected_language="en",
        segments=[],
        duration_ms=1000,
        created_at=datetime.now(timezone.utc),
    )


def analysis_result(content: str) -> AnalysisResult:
    return AnalysisResult(
        content=content,
        model_used="llama3.1",
        prompt_tokens=10,
        completion_tokens=5,
        request_id="",
        created_at=int(datetime.now(timezone.utc).timestamp()),
    )


def install_fakes(
        monkeypatch: pytest.MonkeyPatch,
        db_session: FakeDbSession,
        cache: FakeContextWindow,
        reply: str,
) -> None:
    async def transcribe(audio_path: str) -> stt.TranscribeResult:
        return transcribe_result("I had a rough day")

    async def analyze(
            message: str,
            context: list[CachedMessage],
            http_client: Any,
            base_url: str,
            model: str,
            num_ctx: int,
            session_id: uuid.UUID,
            system_prompt: str | None = None,
    ) -> AnalysisResult:
        # The user message must already be committed when analysis starts.
        assert db_session.events.count("commit") == 1
        db_session.events.append("analyze")
        return analysis_result(reply)

    monkeypatch.setattr(messages_route.stt, "transcribe", transcribe)
    monkeypatch.setattr(messages_route, "analyze", analyze)
    monkeypatch.setattr(messages_route, "context_window_cache", cache)


def call_endpoint(db_session: FakeDbSession) -> CreateMessagesResponse:
    return asyncio.run(
        messages_route.create_messages(
            session_id=db_session.session.id,
            request=cast(Request, FakeRequest()),
            db_session=cast(Any, db_session),
            file=cast(Any, FakeUploadFile(b"audio bytes")),
        )
    )


def test_empty_reply_stores_only_the_user_message(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = make_session()
    db_session = FakeDbSession(session)
    cache = FakeContextWindow()
    install_fakes(monkeypatch, db_session, cache, reply="")

    response = call_endpoint(db_session)

    assert [message.role for message in response.messages] == [MessageRole.USER]
    assert db_session.events == ["commit", "analyze"]
    assert len(db_session.added) == 1

    user_message: Message = db_session.added[0]
    assert user_message.role is MessageRole.USER
    assert isinstance(user_message.transcription_metrics, TranscriptionMetrics)
    assert user_message.analysis_metrics is None
    assert cache.excluded_message_id == user_message.id
    assert cache.appended[0].message_id == user_message.id


def test_non_empty_reply_stores_ordered_user_and_assistant_messages(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = make_session()
    db_session = FakeDbSession(session)
    cache = FakeContextWindow()
    install_fakes(monkeypatch, db_session, cache, reply=LLM_REPLY)

    response = call_endpoint(db_session)

    assert [message.role for message in response.messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert db_session.events == ["commit", "analyze", "commit"]
    assert len(db_session.added) == 2

    user_message: Message = db_session.added[0]
    assistant_message: Message = db_session.added[1]
    assert assistant_message.created_at > user_message.created_at
    assert isinstance(user_message.transcription_metrics, TranscriptionMetrics)
    assert user_message.analysis_metrics is None
    assert isinstance(assistant_message.analysis_metrics, AnalysisMetrics)
    assert assistant_message.transcription_metrics is None
    assert response.messages[1].content == LLM_REPLY
    assert [message.role for message in cache.appended] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
