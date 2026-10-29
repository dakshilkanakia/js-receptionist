import os
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the repo root, one level above backend/
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _async_db_url(url: str) -> str:
    """Hosts like Railway give postgres:// or postgresql://; SQLAlchemy async needs +asyncpg."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix):]
    return url


class Settings:
    database_url: str = _async_db_url(
        os.getenv("DATABASE_URL", "postgresql+asyncpg://js:js@localhost:5432/js_receptionist")
    )
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "anthropic/claude-haiku-5.5")
    tts_voice: str = os.getenv("TTS_VOICE", "aura-2-thalia-en")
    owner_email: str = os.getenv("OWNER_EMAIL", "owner@demo.local")
    owner_password: str = os.getenv("OWNER_PASSWORD", "")
    # True in production (HTTPS): session cookie is only sent over HTTPS.
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    session_secret: str = os.getenv("SESSION_SECRET", "dev-only-secret")
    max_concurrent_calls: int = int(os.getenv("MAX_CONCURRENT_CALLS", "3"))
    calls_per_ip_per_hour: int = int(os.getenv("CALLS_PER_IP_PER_HOUR", "10"))
    max_call_seconds: int = int(os.getenv("MAX_CALL_SECONDS", "600"))
    allowed_origins: list[str] = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]


settings = Settings()
