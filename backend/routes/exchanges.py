import os
import pathlib
import tempfile
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus

from fastapi import File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import DbSession
from db.models import AnalysisMetrics, Exchange, Session, TranscriptionMetrics
from schemas.exchanges import ExchangeResponse, UpdateExchangeRequest
from services import stt
from services.ai_analysis import analyze
from . import session_router

ALLOWED_AUDIO_TYPES: set[str] = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@session_router.post("/sessions/{session_id}/exchanges", response_model=ExchangeResponse, status_code=HTTPStatus.CREATED)
async def create_exchange(
        session_id: uuid.UUID,
        request: Request,
        db_session: DbSession,
        file: UploadFile = File(...),
) -> ExchangeResponse:
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

    http_client = request.app.state.http_client
    ollama_base_url = request.app.state.ollama_base_url
    ollama_model = request.app.state.ollama_model
    ollama_num_ctx = request.app.state.ollama_num_ctx
    t0 = time.time()
    analysis_result = await analyze(
        whisper_result["raw_text"], http_client, ollama_base_url, ollama_model, ollama_num_ctx
    )
    analysis_ms = int(round((time.time() - t0) * 1000))

    exchange_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    exchange = Exchange(
        id=exchange_id,
        session_id=session_id,
        created_at=created_at,
        transcript=whisper_result["raw_text"],
        reflection=analysis_result["reflection"],
        detected_mode=analysis_result["detected_mode"],
        transcription_metrics=TranscriptionMetrics(
            transcript_segments=whisper_result["segments"],
            transcript_duration_ms=whisper_result["duration_ms"],
            detected_language=whisper_result["detected_language"],
            processing_ms=whisper_ms,
            created_at=whisper_result["created_at"],
        ),
        analysis_metrics=AnalysisMetrics(
            prompt_tokens=analysis_result["prompt_tokens"],
            completion_tokens=analysis_result["completion_tokens"],
            request_id=analysis_result["request_id"],
            model_used=analysis_result["model_used"],
            created_at=datetime.fromtimestamp(analysis_result["created_at"], tz=timezone.utc),
            processing_ms=analysis_ms,
        ),
    )
    db_session.add(exchange)

    if session.title is None:
        session.title = whisper_result["raw_text"][:50]

    await db_session.commit()
    await db_session.refresh(exchange)

    return ExchangeResponse(
        id=exchange.id,
        session_id=exchange.session_id,
        transcript=exchange.transcript,
        reflection=exchange.reflection,
        detected_mode=exchange.detected_mode,
        created_at=exchange.created_at.isoformat(),
        filename=file.filename or "",
        content_type=file.content_type,
    )


@session_router.put("/sessions/{session_id}/exchanges/{exchange_id}", response_model=ExchangeResponse)
async def update_exchange(
        session_id: uuid.UUID,
        exchange_id: uuid.UUID,
        request: Request,
        db_session: DbSession,
        body: UpdateExchangeRequest,
) -> ExchangeResponse:
    session = await db_session.get(Session, session_id)
    if session is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    if not session.is_active:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="Session is not active",
        )

    result = await db_session.execute(
        select(Exchange)
        .options(selectinload(Exchange.analysis_metrics))
        .where(Exchange.id == exchange_id, Exchange.session_id == session_id)
    )
    exchange = result.scalar_one_or_none()
    if exchange is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Exchange {exchange_id} not found in session {session_id}",
        )

    http_client = request.app.state.http_client
    ollama_base_url = request.app.state.ollama_base_url
    ollama_model = request.app.state.ollama_model
    ollama_num_ctx = request.app.state.ollama_num_ctx
    t0 = time.time()
    analysis_result = await analyze(
        body.transcript, http_client, ollama_base_url, ollama_model, ollama_num_ctx
    )
    analysis_ms = int(round((time.time() - t0) * 1000))

    exchange.transcript = body.transcript
    exchange.reflection = analysis_result["reflection"]
    exchange.detected_mode = analysis_result["detected_mode"]

    exchange.analysis_metrics.prompt_tokens = analysis_result["prompt_tokens"]
    exchange.analysis_metrics.completion_tokens = analysis_result["completion_tokens"]
    exchange.analysis_metrics.request_id = analysis_result["request_id"]
    exchange.analysis_metrics.model_used = analysis_result["model_used"]
    exchange.analysis_metrics.created_at = datetime.fromtimestamp(
        analysis_result["created_at"], tz=timezone.utc
    )
    exchange.analysis_metrics.processing_ms = analysis_ms

    await db_session.commit()
    await db_session.refresh(exchange)

    return ExchangeResponse(
        id=exchange.id,
        session_id=exchange.session_id,
        transcript=exchange.transcript,
        reflection=exchange.reflection,
        detected_mode=exchange.detected_mode,
        created_at=exchange.created_at.isoformat(),
    )
