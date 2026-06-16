import uuid

from pydantic import BaseModel


class TranscriptionInfo(BaseModel):
    detected_language: str | None
    segments: list[dict]
    duration_ms: int
    processing_ms: int


class AnalysisInfo(BaseModel):
    reflection: str
    detected_mode: str | None
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    request_id: str
    created_at: int | float | None
    processing_ms: int


class CreateEntryResponse(BaseModel):
    id: uuid.UUID
    created_at: str
    filename: str
    content_type: str | None
    raw_transcript: str
    whisper: TranscriptionInfo
    analysis: AnalysisInfo
    total_processing_ms: int
