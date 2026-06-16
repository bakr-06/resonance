import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Entry(Base):
    __tablename__ = "entry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    detected_mode: Mapped[str | None] = mapped_column(String(20))

    transcription_metrics: Mapped["TranscriptionMetrics"] = relationship(
        back_populates="entry", uselist=False
    )
    analysis_metrics: Mapped["AnalysisMetrics"] = relationship(
        back_populates="entry", uselist=False
    )


class TranscriptionMetrics(Base):
    __tablename__ = "transcription_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entry.id"), primary_key=True
    )
    transcript_segments: Mapped[list] = mapped_column(JSONB)
    transcript_duration_ms: Mapped[int] = mapped_column(Integer)
    processing_ms: Mapped[int] = mapped_column(Integer)
    detected_language: Mapped[str | None] = mapped_column(String(10))

    entry: Mapped["Entry"] = relationship(back_populates="transcription_metrics")


class AnalysisMetrics(Base):
    __tablename__ = "analysis_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entry.id"), primary_key=True
    )
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    openrouter_request_id: Mapped[str] = mapped_column(String)
    model_used: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processing_ms: Mapped[int] = mapped_column(Integer)

    entry: Mapped["Entry"] = relationship(back_populates="analysis_metrics")
