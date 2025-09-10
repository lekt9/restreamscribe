from __future__ import annotations

from typing import Optional
import httpx

from app.config import settings


SUMMARY_PROMPT = (
    "You are a world-class livestream summarizer. Given a full transcript, "
    "produce a verbose, structured summary with: (1) title, (2) agenda/timeline with timestamps "
    "if present, (3) key moments and decisions, (4) Q&A highlights, (5) action items, (6) notable quotes, "
    "(7) short abstract (2–3 sentences). Keep sections clearly labeled."
)


class OpenRouterClient:
    def __init__(self, api_key: Optional[str] | None = None, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.model = model or settings.openrouter_model

    async def summarize(self, transcript_text: str, title: Optional[str] = None) -> str:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY not configured")

        system_prompt = SUMMARY_PROMPT
        if title:
            system_prompt += f"\nStream title: {title}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Optional but recommended
            "HTTP-Referer": settings.openrouter_referer,
            "X-Title": settings.openrouter_title,
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Here is the transcript. Provide the detailed summary and include a full transcript section at the end.\n\n"
                        + transcript_text
                    ),
                },
            ],
        }

        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Unexpected OpenRouter response: {data}") from e

