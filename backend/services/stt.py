from datetime import datetime
from typing import TypedDict

import whisper

Model = whisper.Whisper

_model: Model = whisper.load_model("base")


class Segment(TypedDict):
    start: float
    end: float
    text: str
    confidence: float | None


class TranscribeResult(TypedDict):
    raw_text: str
    detected_language: str | None
    segments: list[Segment]
    duration_ms: int
    created_at: datetime


async def transcribe(audio_path: str) -> TranscribeResult:
    result: dict = _model.transcribe(audio_path)
    segments: list[Segment] = [
        {
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "text": s["text"].strip(),
            "confidence": round(s.get("confidence", 0), 3) if s.get("confidence") else None,
        }
        for s in result.get("segments", [])
    ]
    return TranscribeResult(
        raw_text=result["text"],
        detected_language=result["language"],
        segments=segments,
        duration_ms=(result["segments"][-1]["end"]) * 1000,
        created_at=datetime.now()
    )
