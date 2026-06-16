import os
import pathlib
import tempfile
import time
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from fastapi import APIRouter, File, UploadFile, HTTPException, Request

from db.database import DbSession
from db.models import AnalysisMetrics, Entry, TranscriptionMetrics
from schemas.entry import AnalysisInfo, CreateEntryResponse, TranscriptionInfo
from services import stt
from services.ai_analysis import analyze

router: APIRouter = APIRouter()

ALLOWED_AUDIO_TYPES: set[str] = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@router.post("/create_entry", response_model=CreateEntryResponse)
async def create_entry(
        request: Request,
        db_session: DbSession,
        file: UploadFile = File(...),
) -> CreateEntryResponse:
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {file.content_type}. Only WAV and MP3 files are allowed.",
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    suffix: str = pathlib.Path(file.filename).suffix
    content: bytes = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    entry_id: uuid.UUID = uuid.uuid4()
    created_at: datetime = datetime.now(timezone.utc)

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path: str = tmp.name

    t0: float = time.time()
    try:
        whisper_result = await stt.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)
    t1: float = time.time()
    whisper_ms: int = int(round((t1 - t0) * 1000))

    openrouter_client = request.app.state.openrouter_client

    analysis_result = await analyze(whisper_result["raw_text"], openrouter_client)  # type: ignore[arg-type]
    t2: float = time.time()
    analysis_ms: int = int(round((t2 - t1) * 1000))

    entry = Entry(
        id=entry_id,
        text=whisper_result["raw_text"],
        analysis=analysis_result["reflection"],
        created_at=created_at,
        detected_mode=analysis_result["detected_mode"],
        analysis_metrics=AnalysisMetrics(
            prompt_tokens=analysis_result["prompt_tokens"],
            completion_tokens=analysis_result["completion_tokens"],
            openrouter_request_id=analysis_result["request_id"],
            model_used=analysis_result["model_used"],
            created_at=datetime.fromtimestamp(analysis_result["created_at"], tz=timezone.utc),
            processing_ms=analysis_ms,
        ),
        transcription_metrics=TranscriptionMetrics(
            transcript_segments=whisper_result["segments"],
            transcript_duration_ms=whisper_result["duration_ms"],
            processing_ms=whisper_ms,
            detected_language=whisper_result["detected_language"],
        ),
    )

    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    return CreateEntryResponse(
        id=entry_id,
        created_at=created_at.isoformat(),
        filename=file.filename,
        content_type=file.content_type,
        raw_transcript=whisper_result["raw_text"],
        whisper=TranscriptionInfo(
            detected_language=whisper_result["detected_language"],
            segments=whisper_result["segments"],
            duration_ms=whisper_result["duration_ms"],
            processing_ms=whisper_ms,
        ),
        analysis=AnalysisInfo(
            reflection=analysis_result["reflection"],
            detected_mode=analysis_result["detected_mode"],
            model_used=analysis_result["model_used"],
            prompt_tokens=analysis_result["prompt_tokens"],
            completion_tokens=analysis_result["completion_tokens"],
            request_id=analysis_result["request_id"],
            created_at=analysis_result["created_at"],
            processing_ms=analysis_ms,
        ),
        total_processing_ms=whisper_ms + analysis_ms,
    )
