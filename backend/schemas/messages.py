import uuid

from pydantic import BaseModel

from db.models import Message, MessageRole


class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: str

    @classmethod
    def from_message(cls, message: Message) -> "MessageResponse":
        return cls(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at.isoformat(),
        )


class CreateMessagesResponse(BaseModel):
    messages: list[MessageResponse]
