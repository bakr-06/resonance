import os
import pathlib
import tempfile
from http import HTTPStatus

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Request

from services import stt
from services.stt_cleanup import clean_transcript

router = APIRouter()

ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@router.post("/create_entry")
async def create_entry(
        request: Request,
        description_file: UploadFile = File(...)):
    if description_file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {description_file.content_type}. Only WAV and MP3 files are allowed.",
        )

    if not description_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    suffix = pathlib.Path(description_file.filename).suffix
    content = await description_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = await stt.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    cleaned_text = await clean_transcript(raw_text)

    return {
        "transcription": cleaned_text,
    }
