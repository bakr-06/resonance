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
    content, suffix = await validate_audio_file(file)

    whisper_result, whisper_ms = await run_transcription(content, suffix)

    entry_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    openrouter_client = request.app.state.openrouter_client

    analysis_result, analysis_ms = await run_analysis(whisper_result["raw_text"], openrouter_client)

    entry = build_entry(entry_id, created_at, whisper_result, whisper_ms, analysis_result, analysis_ms)
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    return build_response(entry_id, created_at, file, whisper_result, whisper_ms, analysis_result, analysis_ms)


async def validate_audio_file(file: UploadFile) -> tuple[bytes, str]:
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

    return content, pathlib.Path(file.filename).suffix


async def run_transcription(content: bytes, suffix: str) -> tuple[dict, int]:
    """Write audio content to a temp file, transcribe it, and return the result with elapsed ms."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    t0 = time.time()
    try:
        result = await stt.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    elapsed_ms = int(round((time.time() - t0) * 1000))
    return result, elapsed_ms


async def run_analysis(raw_text: str, openrouter_client) -> tuple[dict, int]:
    """Run AI analysis on the transcript and return the result with elapsed ms."""
    t0 = time.time()
    result = await analyze(raw_text, openrouter_client)
    elapsed_ms = int(round((time.time() - t0) * 1000))
    return result, elapsed_ms


def build_entry(
        entry_id: uuid.UUID,
        created_at: datetime,
        whisper_result: dict,
        whisper_ms: int,
        analysis_result: dict,
        analysis_ms: int,
) -> Entry:
    return Entry(
        id=entry_id,
        created_at=created_at,
        transcript=whisper_result["raw_text"],
        analysis=analysis_result["reflection"],
        detected_mode=analysis_result["detected_mode"],
        transcription_metrics=TranscriptionMetrics(
            transcript_segments=whisper_result["segments"],
            transcript_duration_ms=whisper_result["duration_ms"],
            detected_language=whisper_result["detected_language"],
            processing_ms=whisper_ms,
        ),
        analysis_metrics=AnalysisMetrics(
            prompt_tokens=analysis_result["prompt_tokens"],
            completion_tokens=analysis_result["completion_tokens"],
            openrouter_request_id=analysis_result["request_id"],
            model_used=analysis_result["model_used"],
            created_at=datetime.fromtimestamp(analysis_result["created_at"], tz=timezone.utc),
            processing_ms=analysis_ms,
        ),
    )


def build_response(
        entry_id: uuid.UUID,
        created_at: datetime,
        file: UploadFile,
        whisper_result: dict,
        whisper_ms: int,
        analysis_result: dict,
        analysis_ms: int,
) -> CreateEntryResponse:
    return CreateEntryResponse(
        id=entry_id,
        created_at=created_at.isoformat(),
        filename=file.filename,
        content_type=file.content_type,
        raw_transcript=whisper_result["raw_text"],
        total_processing_ms=whisper_ms + analysis_ms,
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
    )
