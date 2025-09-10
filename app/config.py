from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Webhook
    restream_webhook_secret: str | None = Field(default=None, description="Optional webhook signing secret")

    # Groq Whisper
    groq_api_key: str | None = None
    groq_whisper_model: str = "whisper-1"

    # OpenRouter
    openrouter_api_key: str | None = None
    openrouter_base_url: AnyUrl | str = "https://openrouter.ai/api/v1"
    # Default to a safe, configurable model. Change to gemini 2.5 pro when available.
    openrouter_model: str = "google/gemini-2.0-pro"
    openrouter_title: str = "RestreamScribe"
    openrouter_referer: str = "http://localhost:8000"

    # Storage
    database_url: str = "sqlite:///./data.db"
    media_download_dir: str = "./media"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

