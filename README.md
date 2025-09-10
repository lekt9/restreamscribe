RestreamScribe

A FastAPI service that receives Restream webhook events, transcribes audio via Groq Whisper, summarizes with OpenRouter (Gemini), and serves transcripts/summaries for download.

Setup

- Python 3.10+
- Set environment variables in `.env`:
  - `GROQ_API_KEY=...`
  - `OPENROUTER_API_KEY=...`
  - Optional: `OPENROUTER_MODEL=google/gemini-2.0-pro` (override to your preferred Gemini model, e.g. gemini 2.5 when available)
  - Optional: `RESTREAM_WEBHOOK_SECRET=...` (signature verification placeholder)

Install

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints

- `POST /webhook/restream` — Receives webhook payload. Expected fields:
  - `media_url` or `recording_url` (direct downloadable URL to audio/video)
  - `stream_id`, `title`, `started_at`, `ended_at` (optional)
  The service downloads media, transcribes via Groq Whisper (`whisper-1`), then summarizes via OpenRouter (`OPENROUTER_MODEL`).
- `GET /streams` — List streams with status.
- `GET /streams/{id}` — Details including transcript and summary (inline).
- `GET /streams/{id}/transcript.txt` — Download transcript.
- `GET /streams/{id}/summary.txt` — Download summary.
- `GET /` — Minimal UI listing processed streams.

Notes

- Restream signature verification is stubbed; add real HMAC verification once header/algorithm are confirmed.
- The OpenRouter model is configurable. If you want Gemini 2.5 Pro, set `OPENROUTER_MODEL` to the exact model ID from https://openrouter.ai/models.
- The downloader expects `media_url` to be accessible by the server.

