from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True, unique=False, nullable=True)
    title = Column(String, nullable=True)
    media_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    language = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transcript = relationship("Transcript", back_populates="stream", uselist=False, cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="stream", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    stream = relationship("Stream", back_populates="transcript")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    stream_id = Column(Integer, ForeignKey("streams.id"), index=True)
    model = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    stream = relationship("Stream", back_populates="summary")

