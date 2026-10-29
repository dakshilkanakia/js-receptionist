from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.facts.schema import DAY_NAMES, DAYS, Store


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def spoken_time(s: str) -> str:
    t = _t(s)
    hour = t.hour % 12 or 12
    suffix = "AM" if t.hour < 12 else "PM"
    return f"{hour}:{t.minute:02d} {suffix}" if t.minute else f"{hour} {suffix}"


def describe_hours(store: Store) -> str:
    parts = []
    for d in DAYS:
        h = store.hours.get(d)
        parts.append(f"{DAY_NAMES[d]} {spoken_time(h.open)} to {spoken_time(h.close)}" if h else f"{DAY_NAMES[d]} closed")
    return "; ".join(parts)


def open_status(store: Store, now: datetime) -> str:
    """Plain-English open/closed status at `now` (already in the store's timezone)."""
    today = store.hours.get(DAYS[now.weekday()])
    if today and _t(today.open) <= now.time() < _t(today.close):
        return f"open now, until {spoken_time(today.close)} today"
    if today and now.time() < _t(today.open):
        return f"closed right now, opens today at {spoken_time(today.open)}"
    for i in range(1, 8):
        day = now + timedelta(days=i)
        h = store.hours.get(DAYS[day.weekday()])
        if h:
            when = "tomorrow" if i == 1 else DAY_NAMES[DAYS[day.weekday()]]
            return f"closed right now, opens {when} at {spoken_time(h.open)}"
    return "closed"


def now_in(tz: str) -> datetime:
    return datetime.now(ZoneInfo(tz))
