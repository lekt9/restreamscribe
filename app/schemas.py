from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RestreamWebhook(BaseModel):
    # Flexible fields to map Restream-like payloads
    event: Optional[str] = None
    stream_id: Optional[str] = Field(
        default=None, alias="streamId", description="External stream/session id"
    )
    title: Optional[str] = None
    media_url: Optional[str] = Field(default=None, alias="mediaUrl")
    recording_url: Optional[str] = Field(default=None, alias="recordingUrl")
    started_at: Optional[datetime] = Field(default=None, alias="startedAt")
    ended_at: Optional[datetime] = Field(default=None, alias="endedAt")
    data: Optional[dict] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def effective_media_url(self) -> Optional[str]:
        if self.media_url:
            return self.media_url
        if self.recording_url:
            return self.recording_url
        if self.data and isinstance(self.data, dict):
            for key in (
                "recordingUrl",
                "recording_url",
                "mediaUrl",
                "media_url",
            ):
                value = self.data.get(key)
                if value:
                    return value
        return None

    def resolved_stream_id(self) -> Optional[str]:
        if self.stream_id:
            return self.stream_id
        if self.data and isinstance(self.data, dict):
            candidate = self.data.get("streamId") or self.data.get("stream_id")
            if candidate:
                return candidate
        return None

    def resolved_title(self) -> Optional[str]:
        if self.title:
            return self.title
        if self.data and isinstance(self.data, dict):
            title = self.data.get("title")
            if title:
                return title
        return None

    def is_recording_ready_event(self) -> bool:
        event_name = (self.event or "").lower()
        if event_name in {
            "recording.ready",
            "recording_ready",
            "stream.recording.ready",
        }:
            return True
        if self.data and isinstance(self.data, dict):
            nested_event = str(self.data.get("event") or "").lower()
            return nested_event in {
                "recording.ready",
                "recording_ready",
                "stream.recording.ready",
            }
        return False


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
