import os
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the repo root, one level above backend/
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://js:js@localhost:5432/js_receptionist"
    )
    deepgram_api_key: str = os.getenv("DEEPGRAM_API_KEY", "")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "anthropic/claude-haiku-5.5")
    tts_voice: str = os.getenv("TTS_VOICE", "aura-2-thalia-en")
    session_secret: str = os.getenv("SESSION_SECRET", "dev-only-secret")
    max_call_seconds: int = int(os.getenv("MAX_CALL_SECONDS", "600"))
    allowed_origins: list[str] = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]


settings = Settings()
