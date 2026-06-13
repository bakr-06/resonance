import whisper

_model = whisper.load_model("base")


async def transcribe(audio_path: str) -> str:
    result = _model.transcribe(audio_path)
    return result["text"]
