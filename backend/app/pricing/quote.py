"""Deterministic price quotes. The LLM never does arithmetic; it reads these results."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.facts.schema import Facts, fmt_pct

CENT = Decimal("0.01")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class QuoteLine:
    name: str
    qty: Decimal
    billed_qty: Decimal
    unit_price: Decimal
    amount: Decimal


@dataclass
class Quote:
    ok: bool
    lines: list[QuoteLine] = field(default_factory=list)
    subtotal: Decimal = Decimal("0")
    rush: str | None = None
    rush_surcharge: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_tool_result(self) -> dict:
        """Shape sent back to the LLM: plain strings so it reads amounts verbatim."""
        if not self.ok:
            return {"ok": False, "errors": self.errors}
        return {
            "ok": True,
            "lines": [
                f"{l.name}: {_fmt_qty(l.billed_qty)} x ${l.unit_price} = ${l.amount}" for l in self.lines
            ],
            "subtotal": f"${self.subtotal}",
            "rush": self.rush,
            "rush_surcharge": f"${self.rush_surcharge}",
            "total": f"${self.total}",
            "notes": self.notes,
        }


def _fmt_qty(q: Decimal) -> str:
    return str(q.normalize()) if q != q.to_integral() else str(int(q))


def quote(
    facts: Facts,
    items: list[dict],
    addons: list[dict] | None = None,
    rush: str | None = None,
) -> Quote:
    q = Quote(ok=True)
    addons = addons or []
    rush = None if rush in (None, "", "none") else rush

    if not items:
        q.errors.append("No items given.")

    order_items = []
    for entry in items:
        item = facts.item(str(entry.get("id", "")))
        qty = _qty(entry.get("qty"))
        if item is None:
            q.errors.append(f"Unknown item '{entry.get('id')}'. Not in the price list.")
            continue
        if qty is None:
            q.errors.append(f"Invalid quantity for {item.name}.")
            continue
        if item.unit != "lb" and qty != qty.to_integral():
            q.errors.append(f"{item.name} must be a whole number.")
            continue
        billed = qty
        if item.min_qty and qty < item.min_qty:
            billed = Decimal(item.min_qty)
            q.notes.append(
                f"{item.name} has a {item.min_qty} {item.unit} minimum, so {_fmt_qty(qty)} "
                f"{item.unit} is charged as {item.min_qty} {item.unit}."
            )
        order_items.append(item)
        q.lines.append(QuoteLine(item.name, qty, billed, item.price, money(billed * item.price)))

    item_ids = {i.id for i in order_items}
    for entry in addons:
        addon = facts.addon(str(entry.get("id", "")))
        qty = _qty(entry.get("qty", 1))
        if addon is None:
            q.errors.append(f"Unknown add-on '{entry.get('id')}'.")
            continue
        if qty is None or qty != qty.to_integral():
            q.errors.append(f"Invalid quantity for {addon.name}.")
            continue
        if addon.requires_item and addon.requires_item not in item_ids:
            needed = facts.item(addon.requires_item)
            q.errors.append(f"{addon.name} is only available with {needed.name if needed else addon.requires_item}.")
            continue
        q.lines.append(QuoteLine(addon.name, qty, qty, addon.price, money(qty * addon.price)))

    if rush is not None:
        option = facts.rush_option(rush)
        if option is None:
            q.errors.append(f"Unknown rush option '{rush}'.")
        else:
            alterations = [i.name for i in order_items if i.category == "alteration"]
            if alterations:
                q.errors.append(f"Rush service does not apply to alterations ({', '.join(alterations)}).")
            if option.id == "same_day":
                not_eligible = [i.name for i in order_items if not i.same_day_eligible and i.category != "alteration"]
                if not_eligible:
                    q.errors.append(
                        f"Same-day is for dry cleaning only; not available for {', '.join(not_eligible)}."
                    )
            q.rush = option.label
            if option.condition:
                q.notes.append(f"{option.label}: {option.condition}")

    if q.errors:
        q.ok = False
        return q

    q.subtotal = money(sum((l.amount for l in q.lines), Decimal("0")))
    if q.rush:
        option = facts.rush_option(rush)
        q.rush_surcharge = money(q.subtotal * option.surcharge_pct / Decimal(100))
        q.notes.append(f"{option.label} adds {fmt_pct(option.surcharge_pct)}% of the order.")
    q.total = money(q.subtotal + q.rush_surcharge)
    q.notes.append(facts.price_note)
    return q


def _qty(raw) -> Decimal | None:
    try:
        v = Decimal(str(raw))
    except Exception:
        return None
    if not v.is_finite() or v <= 0 or v > 1000:
        return None
    return v
