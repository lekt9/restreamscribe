from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Optional

from fastapi import (
    FastAPI,
    Depends,
    BackgroundTasks,
    Header,
    HTTPException,
    Request,
)
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from pydantic import ValidationError

from app.config import settings
from app.db import Base, engine, get_db
from app.models import Stream
from app.schemas import RestreamWebhook, StreamOut, StreamDetail
from app.services.processing import process_stream

app = FastAPI(title="RestreamScribe", debug=settings.debug)

# Create tables at startup
Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def verify_webhook_signature(
    payload: bytes,
    signature_header: Optional[str],
) -> bool:
    secret = settings.restream_webhook_secret
    if not secret:
        return True

    if not signature_header:
        return False

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_header)


@app.post("/webhook/restream", response_class=PlainTextResponse)
async def restream_webhook(
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    x_restream_signature: Optional[str] = Header(default=None, alias="X-Restream-Signature"),
):
    raw_body = await request.body()

    if not verify_webhook_signature(raw_body, x_restream_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = RestreamWebhook.model_validate_json(raw_body)
    except ValidationError as exc:  # noqa: B904
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc

    if payload.event and not payload.is_recording_ready_event():
        return "ignored"

    media_url = payload.effective_media_url()
    if not media_url:
        raise HTTPException(
            status_code=400,
            detail="Missing media_url / recording_url in payload",
        )

    external_id = payload.resolved_stream_id()
    title = payload.resolved_title()

    stream_query = db.query(Stream)
    stream: Optional[Stream] = None
    if external_id:
        stream = stream_query.filter(Stream.external_id == external_id).one_or_none()
    if stream is None:
        stream = stream_query.filter(Stream.media_url == media_url).one_or_none()

    if stream is None:
        stream = Stream(
            external_id=external_id,
            title=title,
            media_url=media_url,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            status="pending",
        )
        db.add(stream)
    else:
        if external_id and not stream.external_id:
            stream.external_id = external_id
        if title and not stream.title:
            stream.title = title
        stream.media_url = media_url
        if payload.started_at:
            stream.started_at = payload.started_at
        if payload.ended_at:
            stream.ended_at = payload.ended_at
        stream.status = "pending"

    db.commit()
    db.refresh(stream)

    # Kick off background processing
    background.add_task(process_stream, stream.id, media_url)
    return "accepted"


@app.get("/streams", response_model=list[StreamOut])
def list_streams(db: Session = Depends(get_db)):
    streams = db.query(Stream).order_by(Stream.created_at.desc()).all()
    return streams


@app.get("/streams/{stream_id}", response_model=StreamDetail)
def get_stream(stream_id: int, db: Session = Depends(get_db)):
    stream = db.get(Stream, stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Not found")
    transcript_text = stream.transcript.text if stream.transcript else None
    summary_text = stream.summary.text if stream.summary else None
    return StreamDetail(
        id=stream.id,
        external_id=stream.external_id,
        title=stream.title,
        media_url=stream.media_url,
        language=stream.language,
        status=stream.status,
        started_at=stream.started_at,
        ended_at=stream.ended_at,
        created_at=stream.created_at,
        updated_at=stream.updated_at,
        transcript_text=transcript_text,
        summary_text=summary_text,
    )


@app.get("/streams/{stream_id}/transcript.txt", response_class=PlainTextResponse)
def download_transcript(stream_id: int, db: Session = Depends(get_db)):
    stream = db.get(Stream, stream_id)
    if not stream or not stream.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return stream.transcript.text


@app.get("/streams/{stream_id}/summary.txt", response_class=PlainTextResponse)
def download_summary(stream_id: int, db: Session = Depends(get_db)):
    stream = db.get(Stream, stream_id)
    if not stream or not stream.summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return stream.summary.text


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    streams = db.query(Stream).order_by(Stream.created_at.desc()).all()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "streams": streams, "now": datetime.utcnow()},
    )
