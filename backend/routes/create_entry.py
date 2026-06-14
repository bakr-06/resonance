import os
import pathlib
import tempfile
import time
import uuid
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, File, UploadFile, HTTPException, Request

from services import stt
from services.ai_analysis import analyze

router: APIRouter = APIRouter()

ALLOWED_AUDIO_TYPES: set[str] = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@router.post("/create_entry")
async def create_entry(
        request: Request,
        file: UploadFile = File(...)) -> dict[str, Any]:
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
    created_at: float = time.time()

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
    t2: float = time.time()
    cleanup_ms: int = int(round((t2 - t1) * 1000))

    analysis_result = await analyze(whisper_result["raw_text"], openrouter_client)  # type: ignore[arg-type]
    t3: float = time.time()
    analysis_ms: int = int(round((t3 - t2) * 1000))

    return {
        "id": entry_id,
        "created_at": created_at,
        "filename": file.filename,
        "content_type": file.content_type,
        "raw_transcript": whisper_result["raw_text"],
        "detected_language": whisper_result["detected_language"],
        "transcription_segments": whisper_result["segments"],
        "transcription_duration_ms": whisper_result["duration_ms"],
        "reflection": analysis_result["reflection"],
        "detected_mode": analysis_result["detected_mode"],
        "analysis_model_used": analysis_result["model_used"],
        "analysis_prompt_tokens": analysis_result["prompt_tokens"],
        "analysis_completion_tokens": analysis_result["completion_tokens"],
        "openrouter_request_id": analysis_result["request_id"],
        "analysis_created_at": analysis_result["created_at"],
        "whisper_processing_ms": whisper_ms,
        "cleanup_processing_ms": cleanup_ms,
        "analysis_processing_ms": analysis_ms,
        "total_processing_ms": whisper_ms + cleanup_ms + analysis_ms,
    }
