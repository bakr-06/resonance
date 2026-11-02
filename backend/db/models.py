import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SocialStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"

    def __str__(self) -> str:
        return self.value


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"

    def __str__(self) -> str:
        return self.value


class Session(Base):
    __tablename__ = "session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resonance_user.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "message"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("session.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, values_callable=lambda obj: [e.value for e in obj], name="messagerole"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["Session"] = relationship(back_populates="messages")
    transcription_metrics: Mapped["TranscriptionMetrics"] = relationship(
        back_populates="message", uselist=False, cascade="all, delete-orphan"
    )
    analysis_metrics: Mapped["AnalysisMetrics"] = relationship(
        back_populates="message", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_message_session_created_at", "session_id", "created_at", "id"),
    )


class TranscriptionMetrics(Base):
    __tablename__ = "transcription_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message.id"), primary_key=True
    )
    transcript_segments: Mapped[list] = mapped_column(JSONB)
    transcript_duration_ms: Mapped[int] = mapped_column(Integer)
    processing_ms: Mapped[int] = mapped_column(Integer)
    detected_language: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    message: Mapped["Message"] = relationship(back_populates="transcription_metrics")


class AnalysisMetrics(Base):
    __tablename__ = "analysis_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message.id"), primary_key=True
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str] = mapped_column(String)
    model_used: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processing_ms: Mapped[int] = mapped_column(Integer)

    message: Mapped["Message"] = relationship(back_populates="analysis_metrics")


class User(Base):
    __tablename__ = "resonance_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False)
    social_status: Mapped[SocialStatus] = mapped_column(Enum(SocialStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
