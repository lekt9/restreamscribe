from __future__ import annotations

import os
from typing import Optional

from groq import Groq

from app.config import settings


class GroqTranscriber:
    def __init__(self, api_key: Optional[str] | None = None, model: str | None = None) -> None:
        self.client = Groq(api_key=api_key or settings.groq_api_key)
        self.model = model or settings.groq_whisper_model

    def transcribe_file(self, path: str) -> tuple[str, Optional[str]]:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        with open(path, "rb") as f:
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=f,
            )
        # result has .text and possibly other fields; language may not always be present
        text = getattr(result, "text", None) or getattr(result, "output_text", None)
        if not text:
            raise RuntimeError("No transcription text returned from Groq")
        lang = getattr(result, "language", None)
        return text, lang

