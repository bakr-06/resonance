import uuid

from pydantic import BaseModel


class ExchangeResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    transcript: str
    reflection: str
    detected_mode: str | None
    created_at: str
    filename: str = ""
    content_type: str | None = None
