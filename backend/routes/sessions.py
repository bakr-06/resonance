import uuid
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import DbSession
from db.models import Session as SessionModel
from schemas.exchanges import ExchangeResponse
from schemas.sessions import CreateSessionResponse, SessionResponse
from services.ai_analysis import generate_title

from . import session_router


@session_router.post("/sessions", response_model=CreateSessionResponse, status_code=HTTPStatus.CREATED)
async def create_session(
        db_session: DbSession,
) -> CreateSessionResponse:
    session = SessionModel()
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return CreateSessionResponse(
        id=session.id,
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
            title=s.title,
            created_at=s.created_at.isoformat(),
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            is_active=s.is_active,
            exchanges=[],
        )
        for s in sessions
    ]


@session_router.get("/sessions/active", response_model=SessionResponse | None)
async def get_active_session(
        db_session: DbSession,
) -> SessionResponse | None:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.exchanges))
        .where(SessionModel.is_active == True)  # noqa: E712
        .limit(1)
    )

    session: SessionModel | None = result.scalar_one_or_none()
    if session is None:
        return None

    exchanges = sorted(session.exchanges, key=lambda e: e.created_at)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        exchanges=[
            ExchangeResponse(
                id=e.id,
                session_id=e.session_id,
                transcript=e.transcript,
                reflection=e.reflection,
                detected_mode=e.detected_mode,
                created_at=e.created_at.isoformat(),
            )
            for e in exchanges
        ],
    )


@session_router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
        session_id: uuid.UUID,
        db_session: DbSession,
) -> SessionResponse:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.exchanges))
        .where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    exchanges = sorted(session.exchanges, key=lambda e: e.created_at)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        exchanges=[
            ExchangeResponse(
                id=e.id,
                session_id=e.session_id,
                transcript=e.transcript,
                reflection=e.reflection,
                detected_mode=e.detected_mode,
                created_at=e.created_at.isoformat(),
            )
            for e in exchanges
        ],
    )


@session_router.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
        session_id: uuid.UUID,
        request: Request,
        db_session: DbSession,
) -> SessionResponse:
    result = await db_session.execute(
        select(SessionModel)
        .options(selectinload(SessionModel.exchanges))
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

    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)

    transcripts = [e.transcript for e in session.exchanges]
    if transcripts:
        openrouter_client = request.app.state.openrouter_client
        title = await generate_title(transcripts, openrouter_client)
        session.title = title

    await db_session.commit()
    await db_session.refresh(session)

    exchanges = sorted(session.exchanges, key=lambda e: e.created_at)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
        is_active=session.is_active,
        exchanges=[
            ExchangeResponse(
                id=e.id,
                session_id=e.session_id,
                transcript=e.transcript,
                reflection=e.reflection,
                detected_mode=e.detected_mode,
                created_at=e.created_at.isoformat(),
            )
            for e in exchanges
        ],
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

    return Response(status_code=HTTPStatus.NO_CONTENT)
