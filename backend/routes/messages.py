import logging
import os
import pathlib
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from fastapi import File, HTTPException, Request, UploadFile

from db.database import DbSession
from db.models import (
    AnalysisMetrics,
    Message,
    MessageRole,
    Session,
    TranscriptionMetrics,
    User,
)
from schemas.messages import CreateMessagesResponse, MessageResponse
from services import stt
from services.ai_analysis import analyze
from services.context_window import CachedMessage, context_window_cache
from services.user_profile import UserProfile, build_user_profile, compose_system_prompt
from . import session_router

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_TYPES: set[str] = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@session_router.post(
    "/sessions/{session_id}/messages",
    response_model=CreateMessagesResponse,
    status_code=HTTPStatus.CREATED,
)
async def create_messages(
        session_id: uuid.UUID,
        request: Request,
        db_session: DbSession,
        file: UploadFile = File(...),
) -> CreateMessagesResponse:
    session = await db_session.get(Session, session_id)
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    if not session.is_active:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Session is not active",
        )

    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {file.content_type}. Only WAV and MP3 files are allowed.",
        )
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail="Empty file uploaded")

    suffix = pathlib.Path(file.filename).suffix

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    t0 = time.time()
    try:
        whisper_result = await stt.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not whisper_result["raw_text"].strip():
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail="No speech detected in the uploaded audio",
        )

    whisper_ms = int(round((time.time() - t0) * 1000))

    user_message = Message(
        session_id=session_id,
        role=MessageRole.USER,
        content=whisper_result["raw_text"],
        transcription_metrics=TranscriptionMetrics(
            transcript_segments=whisper_result["segments"],
            transcript_duration_ms=whisper_result["duration_ms"],
            detected_language=whisper_result["detected_language"],
            processing_ms=whisper_ms,
            created_at=whisper_result["created_at"],
        ),
    )
    db_session.add(user_message)

    if session.title is None:
        session.title = whisper_result["raw_text"][:50]

    # Commit before analysis: a timeout or a crashed worker must not lose the
    # recording. The reply can always be missing; the user message cannot.
    await db_session.commit()
    await db_session.refresh(user_message)

    await context_window_cache.append(
        session_id=session_id,
        message=_to_cached_message(user_message),
    )

    context: list[CachedMessage] = await context_window_cache.get_messages(
        session_id,
        db_session,
        exclude_message_id=user_message.id,
    )

    http_client = request.app.state.http_client
    ollama_base_url = request.app.state.ollama_base_url
    ollama_model = request.app.state.ollama_model
    ollama_num_ctx = request.app.state.ollama_num_ctx

    # The session is owned by exactly one user, so this is the identity of the
    # person the model is talking to. Missing rows should not cost a recording:
    # the FK makes it a data-integrity bug, not a user-facing error.
    user: User | None = await db_session.get(User, session.user_id)
    profile: UserProfile | None = None
    if user is None:
        logger.warning(
            "User %s for session %s not found; analyzing without a profile",
            session.user_id,
            session_id,
        )
    else:
        profile = build_user_profile(
            name=user.name,
            occupation=user.occupation,
            social_status=user.social_status,
            date_of_birth=user.date_of_birth,
        )

    base_system_prompt: str | None = getattr(
        request.app.state, "analysis_system_prompt", None
    )
    system_prompt: str | None = compose_system_prompt(base_system_prompt, profile)

    t0 = time.time()
    analysis_result = await analyze(
        user_message.content,
        context,
        http_client,
        ollama_base_url,
        ollama_model,
        ollama_num_ctx,
        session_id=session_id,
        system_prompt=system_prompt,
    )
    analysis_ms = int(round((time.time() - t0) * 1000))

    created_messages: list[Message] = [user_message]

    if analysis_result["content"]:
        assistant_message = Message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=analysis_result["content"],
            # The reply must sort after its question even when both are created
            # within the same clock tick.
            created_at=max(
                datetime.now(timezone.utc),
                user_message.created_at + timedelta(milliseconds=1),
            ),
            analysis_metrics=AnalysisMetrics(
                prompt_tokens=analysis_result["prompt_tokens"],
                completion_tokens=analysis_result["completion_tokens"],
                request_id=analysis_result["request_id"],
                model_used=analysis_result["model_used"],
                created_at=datetime.fromtimestamp(
                    analysis_result["created_at"], tz=timezone.utc
                ),
                processing_ms=analysis_ms,
            ),
        )
        db_session.add(assistant_message)
        await db_session.commit()
        await db_session.refresh(assistant_message)
        await context_window_cache.append(
            session_id=session_id,
            message=_to_cached_message(assistant_message),
        )
        created_messages.append(assistant_message)

    return CreateMessagesResponse(
        messages=[MessageResponse.from_message(message) for message in created_messages],
    )


def _to_cached_message(message: Message) -> CachedMessage:
    return CachedMessage(
        message_id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )
