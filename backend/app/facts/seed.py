"""Version 1 of the facts, taken from the homework spec (jscleaners.nyc + real calls)."""

_park_ave = {
    "mon": {"open": "07:30", "close": "18:00"},
    "tue": {"open": "07:30", "close": "18:00"},
    "wed": {"open": "07:30", "close": "18:00"},
    "thu": {"open": "07:30", "close": "18:00"},
    "fri": {"open": "07:30", "close": "18:00"},
    "sat": {"open": "09:00", "close": "17:00"},
    "sun": None,
}

SEED_FACTS: dict = {
    "business": {
        "name": "J's Cleaners",
        "city": "New York City",
        "years": "over 40 years",
        "main_phone": "(212) 716-1177",
        "timezone": "America/New_York",
        "store_count": 15,
        "boroughs": ["Manhattan", "Brooklyn"],
        "locations_url": "jscleaners.nyc/locations",
    },
    "stores": [{"name": "425 Park Ave S", "phone": None, "hours": _park_ave}],
    "services": [
        "Dry cleaning",
        "Shirts",
        "Wash & fold",
        "Comforters and household linens",
        "Sneakers",
        "Wedding dress cleaning and preservation",
        "Seasonal storage",
        "Alterations (tailor in Monday to Friday)",
    ],
    "prices": [
        {"id": "wash_fold", "name": "Wash & fold", "unit": "lb", "price": "2.99",
         "category": "wash_fold", "min_qty": 8},
        {"id": "shirt_hanger", "name": "Shirt on hanger", "unit": "each", "price": "4.95",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "shirt_boxed", "name": "Shirt boxed", "unit": "each", "price": "5.95",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "shirt_hand_pressed", "name": "Hand-pressed shirt", "unit": "each", "price": "13.95",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "pants", "name": "Pants", "unit": "each", "price": "13.45",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "jacket", "name": "Jacket", "unit": "each", "price": "17.45",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "dress", "name": "Dress", "unit": "each", "price": "24.95",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "coat", "name": "Coat", "unit": "each", "price": "49.50",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "gown", "name": "Gown", "unit": "each", "price": "65.00",
         "category": "dry_cleaning", "same_day_eligible": True},
        {"id": "comforter", "name": "Comforter", "unit": "each", "price": "49.00",
         "category": "household"},
        {"id": "sneakers", "name": "Sneakers", "unit": "pair", "price": "22.45",
         "category": "sneakers"},
        {"id": "pants_hem", "name": "Pants hem", "unit": "each", "price": "25.00",
         "category": "alteration"},
    ],
    "addons": [
        {"id": "hang_dry", "name": "Hang-dry", "unit": "piece", "price": "1.00",
         "requires_item": "wash_fold"},
        {"id": "comforter_in_bag", "name": "Comforter in the wash & fold bag", "unit": "each",
         "price": "10.00", "requires_item": "wash_fold"},
    ],
    "price_note": "All prices are starting-at prices. Fabric, size or designer details can add to it.",
    "turnaround": "Usually about 2 days. The plant is closed on weekends.",
    "rush": [
        {"id": "next_day", "label": "Next-day", "surcharge_pct": "50"},
        {"id": "same_day", "label": "Same-day", "surcharge_pct": "100",
         "condition": "Dry cleaning only, dropped off before 9 AM."},
    ],
    "alterations": (
        "Pants hem is $25. Anything else is priced by the tailor at a fitting in the store; "
        "photos aren't enough. The tailor is in Monday to Friday. Rush does not apply to alterations."
    ),
    "pickup_delivery": (
        "Free pickup and delivery anywhere in NYC. Customers leave the bag with the doorman or "
        "front desk. Wash & fold and dry cleaning go in separate bags."
    ),
    "never": [
        "Guarantee that a stain will come out",
        "Promise a pickup time",
        "Say that an order is ready",
        "Handle refunds or complaints",
        "Share other customers' details",
    ],
    "faqs": [],
}
