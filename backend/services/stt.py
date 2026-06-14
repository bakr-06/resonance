import whisper

Model = whisper.Whisper

_model: Model = whisper.load_model("base")

Segment = dict[str, float | str | None]
TranscribeResult = dict[str, str | float | int | None | list[Segment]]


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
    return {
        "raw_text": result["text"],
        "detected_language": result.get("language"),
        "segments": segments,
        "duration_ms": int(round(segments[-1]["end"] * 1000)) if segments else 0,
    }
