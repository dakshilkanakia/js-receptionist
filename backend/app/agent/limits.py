"""Abuse and cost protection for the public call link (in-memory, single instance)."""

import time
from collections import defaultdict, deque

from app.config import settings


class CallLimiter:
    def __init__(self, max_concurrent: int, per_ip_per_hour: int):
        self.max_concurrent = max_concurrent
        self.per_ip_per_hour = per_ip_per_hour
        self.active = 0
        self._starts: dict[str, deque[float]] = defaultdict(deque)

    def _recent(self, key: str) -> deque[float]:
        starts = self._starts[key]
        while starts and time.time() - starts[0] > 3600:
            starts.popleft()
        return starts

    def check(self, key: str | None) -> str | None:
        """Why a new call can't start right now, or None if it can."""
        if self.active >= self.max_concurrent:
            return "Jenny is on other calls right now. Please try again in a minute."
        if key and len(self._recent(key)) >= self.per_ip_per_hour:
            return "You've reached the demo's call limit for this hour. Please try again later."
        return None

    def start(self, key: str | None) -> None:
        self.active += 1
        if key:
            self._recent(key).append(time.time())

    def end(self) -> None:
        self.active = max(0, self.active - 1)


limiter = CallLimiter(settings.max_concurrent_calls, settings.calls_per_ip_per_hour)
