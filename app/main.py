from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

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
    request: Request,
    signature_header: Optional[str],
) -> bool:
    # Placeholder for Restream signature verification; implement if you have spec
    # e.g., HMAC with shared secret over raw body: X-Restream-Signature
    if settings.restream_webhook_secret and signature_header:
        # Add real verification when spec is known
        return True
    return True


@app.post("/webhook/restream", response_class=PlainTextResponse)
async def restream_webhook(
    payload: RestreamWebhook,
    background: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
    x_restream_signature: Optional[str] = Header(default=None, alias="X-Restream-Signature"),
):
    if not verify_webhook_signature(request, x_restream_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    media_url = payload.effective_media_url()
    if not media_url:
        raise HTTPException(status_code=400, detail="Missing media_url / recording_url in payload")

    stream = Stream(
        external_id=payload.stream_id,
        title=payload.title,
        media_url=media_url,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        status="pending",
    )
    db.add(stream)
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
    return templates.TemplateResponse("index.html", {"request": request, "streams": streams, "now": datetime.utcnow()})
