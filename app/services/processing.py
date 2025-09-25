from __future__ import annotations

import os
import asyncio
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models import Stream, Transcript, Summary
from app.services.groq_service import GroqTranscriber
from app.services.openrouter_service import OpenRouterClient


async def download_media(url: str, dest_dir: str) -> str:
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    filename = url.split("?")[0].split("/")[-1] or "stream-media"
    local_path = os.path.join(dest_dir, filename)
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)
    return local_path


async def process_stream(stream_id: int, media_url: str) -> None:
    db: Session = SessionLocal()
    try:
        stream = db.get(Stream, stream_id)
        if not stream:
            return
        # Update status to processing
        stream.status = "processing"
        db.add(stream)
        db.commit()
        db.refresh(stream)

        try:
            # 1) Download
            local_media = await download_media(media_url, settings.media_download_dir)

            # 2) Transcribe (blocking IO — run in thread)
            transcriber = GroqTranscriber()
            loop = asyncio.get_running_loop()
            text, lang = await loop.run_in_executor(None, transcriber.transcribe_file, local_media)

            # Store transcript
            transcript = Transcript(stream_id=stream.id, text=text)
            stream.language = lang
            db.add(transcript)
            db.add(stream)
            db.commit()
            db.refresh(stream)

            # 3) Summarize
            or_client = OpenRouterClient()
            summary_text = await or_client.summarize(text, title=stream.title)
            summary = Summary(stream_id=stream.id, text=summary_text, model=or_client.model)
            db.add(summary)
            stream.status = "completed"
            db.add(stream)
            db.commit()

        except Exception as e:  # noqa: BLE001
            # On failure, try to persist error status
            try:
                stream = db.get(Stream, stream_id)
                if stream:
                    stream.status = f"failed: {e}"
                    db.add(stream)
                    db.commit()
            finally:
                raise
    finally:
        db.close()
