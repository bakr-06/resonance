import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    exchanges: Mapped[list["Exchange"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Exchange(Base):
    __tablename__ = "exchange"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("session.id"), nullable=False
    )
    transcript: Mapped[str] = mapped_column(Text)
    reflection: Mapped[str] = mapped_column(Text)
    detected_mode: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["Session"] = relationship(back_populates="exchanges")
    transcription_metrics: Mapped["TranscriptionMetrics"] = relationship(
        back_populates="exchange", uselist=False, cascade="all, delete-orphan"
    )
    analysis_metrics: Mapped["AnalysisMetrics"] = relationship(
        back_populates="exchange", uselist=False, cascade="all, delete-orphan"
    )


class TranscriptionMetrics(Base):
    __tablename__ = "transcription_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchange.id"), primary_key=True
    )
    transcript_segments: Mapped[list] = mapped_column(JSONB)
    transcript_duration_ms: Mapped[int] = mapped_column(Integer)
    processing_ms: Mapped[int] = mapped_column(Integer)
    detected_language: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    exchange: Mapped["Exchange"] = relationship(back_populates="transcription_metrics")


class AnalysisMetrics(Base):
    __tablename__ = "analysis_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exchange.id"), primary_key=True
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    openrouter_request_id: Mapped[str] = mapped_column(String)
    model_used: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processing_ms: Mapped[int] = mapped_column(Integer)

    exchange: Mapped["Exchange"] = relationship(back_populates="analysis_metrics")
