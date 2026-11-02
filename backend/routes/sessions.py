import logging
import uuid
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import DbSession
from db.models import MessageRole, Session as SessionModel
from logging_config import session_log_extra
from schemas.messages import MessageResponse
from schemas.sessions import CreateSessionRequest, CreateSessionResponse, SessionResponse
from services.ai_analysis import generate_title
from services.context_window import context_window_cache
from . import session_router

logger = logging.getLogger(__name__)


@session_router.post("/sessions", response_model=CreateSessionResponse, status_code=HTTPStatus.CREATED)
async def create_session(
    db_session: DbSession,
    body: CreateSessionRequest,
) -> CreateSessionResponse:
    from db.models import User

    user = await db_session.get(User, body.user_id)
    if user is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"User {body.user_id} not found",
        )

    session = SessionModel(user_id=body.user_id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    logger.info("Created session id=%s", session.id, extra=session_log_extra(session.id))
    return CreateSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        is_active=session.is_active,
    )


@session_router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
        db_session: DbSession,
) -> list[SessionResponse]:
    result = await db_session.execute(
        select(SessionModel).order_by(SessionModel.created_at.desc())
    )

    sessions = result.scalars().all()
    return [
        SessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            is_active=s.is_active,
            # The list endpoint does not load messages, so an empty list here
            # means "not loaded", not "this session has no messages".
            messages=[],
        )
        for s in sessions
    ]


@session_router.get("/sessions/active", response_model=SessionResponse | None)
async def get_active_session(
        db_session: DbSession,
) -> SessionResponse | None:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.messages))
        .where(SessionModel.is_active == True)  # noqa: E712
        .limit(1)
    )

    session: SessionModel | None = result.scalar_one_or_none()
    if session is None:
        return None

    messages = sorted(session.messages, key=lambda m: (m.created_at, m.id))
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        messages=[MessageResponse.from_message(m) for m in messages],
    )



@session_router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
        session_id: uuid.UUID,
        db_session: DbSession,
) -> SessionResponse:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.messages))
        .where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    messages = sorted(session.messages, key=lambda m: (m.created_at, m.id))
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        messages=[MessageResponse.from_message(m) for m in messages],
    )



@session_router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
        session_id: uuid.UUID,
        request: Request,
        db_session: DbSession,
) -> SessionResponse:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.messages))
        .where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    if not session.is_active:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Session is already ended",
        )

    extra: dict[str, str] = session_log_extra(session_id)
    logger.info("Ending session id=%s with %d messages", session_id, len(session.messages), extra=extra)

    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)

    transcripts = [
        message.content
        for message in session.messages
        if message.role is MessageRole.USER
    ]
    if transcripts:
        logger.info("Generating title for session id=%s from %d transcripts", session_id, len(transcripts), extra=extra)
        http_client = request.app.state.http_client
        ollama_base_url = request.app.state.ollama_base_url
        ollama_model = request.app.state.ollama_model
        ollama_num_ctx = request.app.state.ollama_num_ctx
        title = await generate_title(
            transcripts,
            http_client,
            ollama_base_url,
            ollama_model,
            ollama_num_ctx,
            session_id=session_id,
        )
        if title:
            session.title = title
        else:
            logger.warning("Title generation returned empty for session id=%s", session_id, extra=extra)
    else:
        logger.info("Session id=%s has no transcripts, skipping title generation", session_id, extra=extra)

    await db_session.commit()
    await db_session.refresh(session)
    await context_window_cache.clear(session_id)
    logger.info("Session id=%s ended (title=%r)", session_id, session.title, extra=extra)

    messages = sorted(session.messages, key=lambda m: (m.created_at, m.id))
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        messages=[MessageResponse.from_message(m) for m in messages],
    )



@session_router.delete("/sessions/{session_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_session(
        session_id: uuid.UUID,
        db_session: DbSession,
) -> Response:
    session = await db_session.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    await db_session.delete(session)
    await db_session.commit()
    await context_window_cache.clear(session_id)

    return Response(status_code=HTTPStatus.NO_CONTENT)
