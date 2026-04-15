from __future__ import annotations

PINCODE_MAP = {
    "800001": {"state": "Bihar", "district": "Patna"},
    "411001": {"state": "Maharashtra", "district": "Pune"},
    "462001": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "560001": {"state": "Karnataka", "district": "Bengaluru Urban"},
}

KEYWORD_MAP = {
    "patna": {"state": "Bihar", "district": "Patna"},
    "bihar": {"state": "Bihar", "district": "Patna"},
    "pune": {"state": "Maharashtra", "district": "Pune"},
    "maharashtra": {"state": "Maharashtra", "district": "Pune"},
    "bhopal": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "madhya pradesh": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "bengaluru": {"state": "Karnataka", "district": "Bengaluru Urban"},
    "karnataka": {"state": "Karnataka", "district": "Bengaluru Urban"},
}


def resolve_location(text: str, location_hint: str | None = None, default_state: str = "Delhi", default_district: str = "New Delhi") -> dict:
    haystack = f"{text} {location_hint or ''}".lower()
    for pin, value in PINCODE_MAP.items():
        if pin in haystack:
            return {"pincode": pin, **value}
    for key, value in KEYWORD_MAP.items():
        if key in haystack:
            return {"pincode": None, **value}
    return {"pincode": None, "state": default_state, "district": default_district}
