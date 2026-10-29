from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.agent.prompt import build_system_prompt
from app.facts.hours import open_status
from app.facts.schema import Facts, fmt_pct
from app.facts.seed import SEED_FACTS

NY = ZoneInfo("America/New_York")


@pytest.fixture
def facts() -> Facts:
    return Facts.model_validate(SEED_FACTS)


@pytest.mark.parametrize(
    "when, expected",
    [
        ("2026-10-29 08:00", "open now, until 6 PM today"),            # Thu
        ("2026-10-29 06:00", "closed right now, opens today at 7:30 AM"),
        ("2026-10-30 19:00", "closed right now, opens tomorrow at 9 AM"),  # Fri night -> Sat
        ("2026-10-31 12:00", "open now, until 5 PM today"),             # Sat
        ("2026-10-31 18:00", "closed right now, opens Monday at 7:30 AM"),
        ("2026-11-01 10:00", "closed right now, opens tomorrow at 7:30 AM"),  # Sun
    ],
)
def test_open_status(facts, when, expected):
    now = datetime.fromisoformat(when).replace(tzinfo=NY)
    assert open_status(facts.stores[0], now) == expected


@pytest.mark.parametrize("raw, out", [("50", "50"), ("100", "100"), ("12.50", "12.5")])
def test_fmt_pct(raw, out):
    assert fmt_pct(Decimal(raw)) == out


def test_prompt_contains_facts_and_no_sci_notation(facts):
    p = build_system_prompt(facts, datetime(2026, 10, 29, 8, 0, tzinfo=NY))
    assert "$13.45" in p and "jscleaners.nyc/locations" in p and "(212) 716-1177" in p
    assert "adds 50% of the order" in p and "E+" not in p
