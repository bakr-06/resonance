import os
import tempfile
from http import HTTPStatus

from fastapi import FastAPI, File, UploadFile, HTTPException

import stt

app = FastAPI()

ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3"}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {file.content_type}. Only WAV and MP3 files are allowed.",
        )

    suffix = ".wav" if "wav" in file.content_type or "wave" in file.content_type else ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        transcription = stt.transcribe(tmp_path)
    finally:
        os.unlink(tmp_path)

    return {"filename": file.filename, "content_type": file.content_type, "text": transcription}
