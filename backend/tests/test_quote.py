from decimal import Decimal

import pytest

from app.facts.schema import Facts
from app.facts.seed import SEED_FACTS
from app.pricing.quote import quote


@pytest.fixture
def facts() -> Facts:
    return Facts.model_validate(SEED_FACTS)


def total(q) -> Decimal:
    assert q.ok, q.errors
    return q.total


def test_wash_fold_minimum_applied(facts):
    q = quote(facts, [{"id": "wash_fold", "qty": 5}])
    assert total(q) == Decimal("23.92")
    assert any("8 lb minimum" in n for n in q.notes)


def test_wash_fold_over_minimum_with_hang_dry(facts):
    q = quote(facts, [{"id": "wash_fold", "qty": 10}], [{"id": "hang_dry", "qty": 3}])
    assert total(q) == Decimal("32.90")


def test_wash_fold_fractional_pounds(facts):
    assert total(quote(facts, [{"id": "wash_fold", "qty": 12.5}])) == Decimal("37.38")


def test_comforter_in_bag(facts):
    q = quote(facts, [{"id": "wash_fold", "qty": 8}], [{"id": "comforter_in_bag", "qty": 1}])
    assert total(q) == Decimal("33.92")


def test_addon_requires_wash_fold(facts):
    q = quote(facts, [{"id": "pants", "qty": 1}], [{"id": "hang_dry", "qty": 2}])
    assert not q.ok


def test_next_day_rush_is_half_of_order(facts):
    q = quote(facts, [{"id": "shirt_hanger", "qty": 3}, {"id": "pants", "qty": 2}], rush="next_day")
    assert q.subtotal == Decimal("41.75")
    assert q.rush_surcharge == Decimal("20.88")
    assert total(q) == Decimal("62.63")


def test_same_day_doubles(facts):
    assert total(quote(facts, [{"id": "coat", "qty": 1}], rush="same_day")) == Decimal("99.00")


def test_same_day_not_for_wash_fold(facts):
    q = quote(facts, [{"id": "wash_fold", "qty": 10}], rush="same_day")
    assert not q.ok and "dry cleaning only" in q.errors[0]


def test_same_day_not_for_comforter_or_sneakers(facts):
    q = quote(facts, [{"id": "comforter", "qty": 1}, {"id": "sneakers", "qty": 1}], rush="same_day")
    assert not q.ok


def test_next_day_ok_for_wash_fold(facts):
    assert total(quote(facts, [{"id": "wash_fold", "qty": 8}], rush="next_day")) == Decimal("35.88")


def test_no_rush_on_alterations(facts):
    q = quote(facts, [{"id": "pants_hem", "qty": 1}], rush="next_day")
    assert not q.ok and "alterations" in q.errors[0]


def test_pants_hem(facts):
    assert total(quote(facts, [{"id": "pants_hem", "qty": 2}])) == Decimal("50.00")


def test_unknown_item_is_error_not_guess(facts):
    q = quote(facts, [{"id": "leather_jacket", "qty": 1}])
    assert not q.ok


@pytest.mark.parametrize("qty", [0, -1, "abc", None, 1.5])
def test_bad_quantities(facts, qty):
    assert not quote(facts, [{"id": "shirt_hanger", "qty": qty}]).ok


def test_rush_none_string(facts):
    assert total(quote(facts, [{"id": "dress", "qty": 1}], rush="none")) == Decimal("24.95")


def test_mixed_big_order(facts):
    items = [
        {"id": "shirt_boxed", "qty": 5},       # 29.75
        {"id": "jacket", "qty": 1},            # 17.45
        {"id": "gown", "qty": 1},              # 65.00
        {"id": "wash_fold", "qty": 9},         # 26.91
        {"id": "sneakers", "qty": 2},          # 44.90
    ]
    q = quote(facts, items, [{"id": "hang_dry", "qty": 4}], rush="next_day")  # +4.00
    assert q.subtotal == Decimal("188.01")
    assert q.rush_surcharge == Decimal("94.01")  # 94.005 rounds half up
    assert total(q) == Decimal("282.02")


def test_tool_result_has_starting_at_note(facts):
    r = quote(facts, [{"id": "pants", "qty": 1}]).as_tool_result()
    assert r["total"] == "$13.45"
    assert any("starting-at" in n for n in r["notes"])


def test_rush_note_reads_naturally(facts):
    q = quote(facts, [{"id": "pants", "qty": 1}], rush="next_day")
    assert "adds 50% of the order" in " ".join(q.notes)


def test_note_phone_digits_accumulates_and_completes():
    from app.agent.tools import note_phone_digits
    d, r = note_phone_digits("", "2 1 2")
    assert r == {"so_far": "212", "count": 3, "complete": False}
    d, r = note_phone_digits(d, "555")
    d, r = note_phone_digits(d, "zero? 0 1 4 7")
    assert r["complete"] and d == "2125550147"
    _, r = note_phone_digits(d, "9")
    assert r["too_many"]
    d, r = note_phone_digits("", "1 212 555 0147")  # leading country code dropped
    assert r["complete"] and d == "2125550147"
    d, r = note_phone_digits("2125", "917", restart=True)
    assert d == "917"
