from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class RestreamWebhook(BaseModel):
    # Flexible fields to map common Restream-like payloads
    event: Optional[str] = None
    stream_id: Optional[str] = Field(default=None, description="External stream/session id")
    title: Optional[str] = None
    media_url: Optional[str] = Field(default=None, description="Direct downloadable audio/video URL")
    recording_url: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    # Raw passthrough
    data: Optional[dict] = None

    def effective_media_url(self) -> Optional[str]:
        return self.media_url or self.recording_url or (self.data or {}).get("media_url") or (self.data or {}).get("recording_url")


class StreamOut(BaseModel):
    id: int
    external_id: Optional[str]
    title: Optional[str]
    media_url: Optional[str]
    language: Optional[str]
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StreamDetail(StreamOut):
    transcript_text: Optional[str] = None
    summary_text: Optional[str] = None

