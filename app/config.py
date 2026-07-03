"""Application settings loaded once from the environment (.env).

Uses pydantic-settings so values are validated and typed. A single cached
`settings` instance is imported everywhere — no repeated env parsing.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (folder that holds .env), resolved independently of the cwd.
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"
    secret_key: str = "dev-secret"

    # Database
    database_url: str = "postgresql+asyncpg://pultrack:pultrack@localhost:55432/pultrack"

    # Redis (optional)
    redis_url: str | None = None

    # Telegram
    telegram_bot_token: str = ""
    webhook_base_url: str = ""
    telegram_webhook_secret: str = "webhook-secret"

    # AI provider: "local" (free, no API key) or "openai" (paid, optional)
    ai_provider: str = "local"
    whisper_model: str = "base"       # faster-whisper: tiny|base|small|medium
    whisper_language: str = "uz"      # force language ("" = auto-detect)

    # Groq (FREE Whisper large-v3 + LLM — best Uzbek, deploy-friendly).
    # If set, it is used for voice transcription AND message understanding.
    groq_api_key: str = ""
    groq_transcribe_model: str = "whisper-large-v3"
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenAI (only used when ai_provider == "openai")
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_transcribe_model: str = "whisper-1"

    # Auth (JWT)
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    # Comma-separated list of allowed frontend origins for CORS ("*" = any).
    cors_origins: str = "*"

    # Dashboard (legacy single-tenant fallback, kept for the seed demo)
    dashboard_user_id: int | None = None

    # Temporary, secret-gated login for demoing production before the
    # Telegram Login Widget is fully verified. Empty = disabled.
    demo_access_key: str = ""

    # Dashboard base URL, used by the bot's /login command to send a direct
    # sign-in link (bypasses the Telegram Login Widget's oauth.telegram.org
    # confirmation-message delivery, which can be unreliable in some regions).
    dashboard_url: str = "http://localhost:5500"

    @field_validator("dashboard_user_id", "redis_url", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        """Treat empty .env values ("") as unset so optional fields stay None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def use_webhook(self) -> bool:
        """True when a public URL is set → run bot via webhook, else long-polling."""
        return bool(self.webhook_base_url)

    @property
    def telegram_webhook_path(self) -> str:
        return f"/telegram/webhook/{self.telegram_webhook_secret}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
