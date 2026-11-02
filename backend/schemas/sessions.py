import uuid

from pydantic import BaseModel

from schemas.exchanges import ExchangeResponse


class CreateSessionRequest(BaseModel):
    user_id: uuid.UUID


class CreateSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    created_at: str
    is_active: bool


class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    created_at: str
    ended_at: str | None
    is_active: bool
    exchanges: list[ExchangeResponse] = []
