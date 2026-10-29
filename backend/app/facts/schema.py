"""The facts the receptionist is allowed to state. Owners edit these in the dashboard."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}

Category = Literal["dry_cleaning", "wash_fold", "household", "sneakers", "alteration"]


class Business(BaseModel):
    name: str
    city: str
    years: str
    main_phone: str
    timezone: str = "America/New_York"
    store_count: int
    boroughs: list[str]
    locations_url: str


class OpenHours(BaseModel):
    open: str = Field(pattern=r"^\d{2}:\d{2}$")   # 24h "07:30"
    close: str = Field(pattern=r"^\d{2}:\d{2}$")


class Store(BaseModel):
    name: str
    phone: str | None = None
    hours: dict[str, OpenHours | None]  # day key -> hours, None = closed

    @field_validator("hours")
    @classmethod
    def all_days(cls, v: dict) -> dict:
        missing = [d for d in DAYS if d not in v]
        if missing:
            raise ValueError(f"hours missing days: {missing}")
        return v


class PriceItem(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    unit: Literal["each", "lb", "pair"]
    price: Decimal = Field(ge=0, decimal_places=2)
    category: Category
    min_qty: int | None = None
    same_day_eligible: bool = False


class Addon(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    unit: Literal["each", "piece"]
    price: Decimal = Field(ge=0, decimal_places=2)
    requires_item: str | None = None  # addon only valid if this item is in the order


class RushOption(BaseModel):
    id: Literal["next_day", "same_day"]
    label: str
    surcharge_pct: Decimal = Field(ge=0)
    condition: str | None = None


def fmt_pct(p: Decimal) -> str:
    """50 -> "50", 12.50 -> "12.5" (Decimal.normalize() would give "5E+1")."""
    return f"{p:f}".rstrip("0").rstrip(".") if "." in f"{p:f}" else f"{p:f}"


class FAQ(BaseModel):
    question: str
    answer: str
    unanswered_id: int | None = None


class Facts(BaseModel):
    business: Business
    stores: list[Store]
    services: list[str]
    prices: list[PriceItem]
    addons: list[Addon]
    price_note: str
    turnaround: str
    rush: list[RushOption]
    alterations: str
    pickup_delivery: str
    never: list[str]
    faqs: list[FAQ] = []

    @model_validator(mode="after")
    def unique_ids(self) -> "Facts":
        ids = [p.id for p in self.prices] + [a.id for a in self.addons]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate price/addon ids: {sorted(dupes)}")
        item_ids = {p.id for p in self.prices}
        for a in self.addons:
            if a.requires_item and a.requires_item not in item_ids:
                raise ValueError(f"addon {a.id} requires unknown item {a.requires_item}")
        return self

    def item(self, item_id: str) -> PriceItem | None:
        return next((p for p in self.prices if p.id == item_id), None)

    def addon(self, addon_id: str) -> Addon | None:
        return next((a for a in self.addons if a.id == addon_id), None)

    def rush_option(self, rush_id: str) -> RushOption | None:
        return next((r for r in self.rush if r.id == rush_id), None)
