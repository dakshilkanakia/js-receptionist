"""Persists one call: transcript turns, consent, and the final outcome."""

import time
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import delete, update

from app.db.models import Call, TranscriptTurn
from app.db.session import SessionLocal


class CallRecorder:
    def __init__(self, call_id: int):
        self.call_id = call_id
        self.consent = True
        self.callback_saved = False
        self.unanswered_logged = False
        self.user_turns = 0
        self.phone_digits = ""  # callback number collected across turns
        self._idx = 0
        self._started = time.monotonic()
        self._finalized = False

    async def add_turn(self, role: str, text: str | None, interrupted: bool = False) -> None:
        if role == "user" and text:
            self.user_turns += 1
        if not self.consent or not text or not text.strip():
            return
        self._idx += 1
        try:
            async with SessionLocal() as s:
                s.add(TranscriptTurn(call_id=self.call_id, idx=self._idx, role=role,
                                     text=text.strip(), interrupted=interrupted))
                await s.commit()
        except Exception:
            # A failed transcript write must never break the live call.
            logger.exception(f"call {self.call_id}: failed to save transcript turn")

    async def decline_consent(self) -> None:
        """Caller declined transcription: delete what we stored and stop storing."""
        self.consent = False
        async with SessionLocal() as s:
            await s.execute(delete(TranscriptTurn).where(TranscriptTurn.call_id == self.call_id))
            await s.execute(update(Call).where(Call.id == self.call_id).values(consent_declined=True))
            await s.commit()
        logger.info(f"call {self.call_id}: consent declined, transcript purged")

    def loggable(self, text: str | None) -> str:
        """Turn text for server logs. Logs are storage too, so withhold it after a decline."""
        if not self.consent:
            return "[withheld: caller declined transcription]"
        return text or ""

    def outcome(self, duration_s: int) -> str:
        if self.callback_saved:
            return "callback_requested"
        if self.unanswered_logged:
            return "unanswered"
        if self.user_turns == 0 or duration_s < 10:
            return "abandoned"
        return "answered"

    async def finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        duration = int(time.monotonic() - self._started)
        async with SessionLocal() as s:
            await s.execute(
                update(Call)
                .where(Call.id == self.call_id)
                .values(
                    ended_at=datetime.now(timezone.utc),
                    duration_s=duration,
                    outcome=self.outcome(duration),
                    has_unanswered=self.unanswered_logged,
                )
            )
            await s.commit()
        logger.info(f"call {self.call_id}: ended after {duration}s, outcome={self.outcome(duration)}")
