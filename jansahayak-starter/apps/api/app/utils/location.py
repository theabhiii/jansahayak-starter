from __future__ import annotations

import re
import httpx

PINCODE_MAP = {
    "110001": {"state": "Delhi", "district": "New Delhi"},
    "110002": {"state": "Delhi", "district": "Central Delhi"},
    "560001": {"state": "Karnataka", "district": "Bengaluru Urban"},
    "411001": {"state": "Maharashtra", "district": "Pune"},
    "400001": {"state": "Maharashtra", "district": "Mumbai"},
    "462001": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "800001": {"state": "Bihar", "district": "Patna"},
    "700001": {"state": "West Bengal", "district": "Kolkata"},
    "226001": {"state": "Uttar Pradesh", "district": "Lucknow"},
    "600001": {"state": "Tamil Nadu", "district": "Chennai"},
    "500001": {"state": "Telangana", "district": "Hyderabad"},
    "302001": {"state": "Rajasthan", "district": "Jaipur"},
    "682001": {"state": "Kerala", "district": "Ernakulam"},
    "380001": {"state": "Gujarat", "district": "Ahmedabad"},
}

STATE_DEFAULT_DISTRICT = {
    "Andhra Pradesh": "Amaravati",
    "Arunachal Pradesh": "Itanagar",
    "Assam": "Kamrup Metropolitan",
    "Bihar": "Patna",
    "Chhattisgarh": "Raipur",
    "Delhi": "New Delhi",
    "Goa": "North Goa",
    "Gujarat": "Ahmedabad",
    "Haryana": "Gurugram",
    "Himachal Pradesh": "Shimla",
    "Jharkhand": "Ranchi",
    "Karnataka": "Bengaluru Urban",
    "Kerala": "Thiruvananthapuram",
    "Madhya Pradesh": "Bhopal",
    "Maharashtra": "Mumbai",
    "Manipur": "Imphal West",
    "Meghalaya": "East Khasi Hills",
    "Mizoram": "Aizawl",
    "Nagaland": "Kohima",
    "Odisha": "Khordha",
    "Punjab": "Ludhiana",
    "Rajasthan": "Jaipur",
    "Sikkim": "Gangtok",
    "Tamil Nadu": "Chennai",
    "Telangana": "Hyderabad",
    "Tripura": "West Tripura",
    "Uttar Pradesh": "Lucknow",
    "Uttarakhand": "Dehradun",
    "West Bengal": "Kolkata",
}

KEYWORD_MAP = {
    "new delhi": {"state": "Delhi", "district": "New Delhi"},
    "delhi": {"state": "Delhi", "district": "New Delhi"},
    "patna": {"state": "Bihar", "district": "Patna"},
    "bihar": {"state": "Bihar", "district": "Patna"},
    "pune": {"state": "Maharashtra", "district": "Pune"},
    "mumbai": {"state": "Maharashtra", "district": "Mumbai"},
    "maharashtra": {"state": "Maharashtra", "district": "Mumbai"},
    "bhopal": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "madhya pradesh": {"state": "Madhya Pradesh", "district": "Bhopal"},
    "bengaluru": {"state": "Karnataka", "district": "Bengaluru Urban"},
    "bangalore": {"state": "Karnataka", "district": "Bengaluru Urban"},
    "karnataka": {"state": "Karnataka", "district": "Bengaluru Urban"},
    "hyderabad": {"state": "Telangana", "district": "Hyderabad"},
    "telangana": {"state": "Telangana", "district": "Hyderabad"},
    "chennai": {"state": "Tamil Nadu", "district": "Chennai"},
    "tamil nadu": {"state": "Tamil Nadu", "district": "Chennai"},
    "kolkata": {"state": "West Bengal", "district": "Kolkata"},
    "west bengal": {"state": "West Bengal", "district": "Kolkata"},
    "lucknow": {"state": "Uttar Pradesh", "district": "Lucknow"},
    "uttar pradesh": {"state": "Uttar Pradesh", "district": "Lucknow"},
    "jaipur": {"state": "Rajasthan", "district": "Jaipur"},
    "rajasthan": {"state": "Rajasthan", "district": "Jaipur"},
    "ahmedabad": {"state": "Gujarat", "district": "Ahmedabad"},
    "gujarat": {"state": "Gujarat", "district": "Ahmedabad"},
    "thiruvananthapuram": {"state": "Kerala", "district": "Thiruvananthapuram"},
    "kerala": {"state": "Kerala", "district": "Thiruvananthapuram"},
}


def _extract_pincode(haystack: str) -> str | None:
    match = re.search(r"\b(\d{6})\b", haystack)
    return match.group(1) if match else None


def _resolve_pincode_online(pin: str) -> dict | None:
    # India Post public pincode API fallback for broader coverage.
    try:
        with httpx.Client(timeout=4.0) as client:
            response = client.get(f"https://api.postalpincode.in/pincode/{pin}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or not payload:
                return None
            block = payload[0] if isinstance(payload[0], dict) else {}
            offices = block.get("PostOffice") or []
            if not isinstance(offices, list) or not offices:
                return None
            first = offices[0] if isinstance(offices[0], dict) else {}
            state = first.get("State")
            district = first.get("District") or first.get("Division")
            if state and district:
                return {"state": state, "district": district}
    except Exception:
        return None
    return None


def resolve_location(text: str, location_hint: str | None = None, default_state: str = "Delhi", default_district: str = "New Delhi") -> dict:
    haystack = f"{text} {location_hint or ''}".lower()

    pin = _extract_pincode(haystack)
    if pin and pin in PINCODE_MAP:
        loc = PINCODE_MAP[pin]
        return {"pincode": pin, "state": loc["state"], "district": loc["district"], "matched_by": "pincode"}
    if pin:
        online = _resolve_pincode_online(pin)
        if online:
            return {"pincode": pin, "state": online["state"], "district": online["district"], "matched_by": "pincode-online"}

    for key, value in KEYWORD_MAP.items():
        if key in haystack:
            return {"pincode": pin, "state": value["state"], "district": value["district"], "matched_by": f"keyword:{key}"}

    for state, district in STATE_DEFAULT_DISTRICT.items():
        if state.lower() in haystack:
            return {"pincode": pin, "state": state, "district": district, "matched_by": f"state:{state}"}

    return {
        "pincode": pin,
        "state": default_state,
        "district": default_district,
        "matched_by": "default",
    }
