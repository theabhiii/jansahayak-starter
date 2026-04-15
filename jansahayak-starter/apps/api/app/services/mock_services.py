from __future__ import annotations

STATE_PORTALS = {
    "Delhi": "https://delhi.gov.in",
    "Bihar": "https://state.bihar.gov.in",
    "Maharashtra": "https://www.maharashtra.gov.in",
    "Madhya Pradesh": "https://mp.gov.in",
    "Karnataka": "https://www.karnataka.gov.in",
    "Tamil Nadu": "https://www.tn.gov.in",
    "Telangana": "https://www.telangana.gov.in",
    "Uttar Pradesh": "https://up.gov.in",
    "Rajasthan": "https://rajasthan.gov.in",
    "West Bengal": "https://wb.gov.in",
    "Gujarat": "https://gujaratindia.gov.in",
    "Kerala": "https://kerala.gov.in",
}


def check_eligibility(query: str, state: str) -> dict:
    return {
        "eligible": "likely",
        "reason": (
            f"Eligibility appears likely based on your context in {state}. "
            "Final confirmation requires official criteria, category, and applicant documents."
        ),
    }



def application_status(reference_id: str | None = None) -> dict:
    return {
        "status": "mocked",
        "message": "This is a demo status endpoint. In production, this would call a live application-status system.",
    }



def route_grievance(issue: str, state: str, district: str) -> dict:
    issue_l = issue.lower()

    if any(token in issue_l for token in ["ration", "pds", "food card"]):
        department = "District Food and Civil Supplies Office"
    elif any(token in issue_l for token in ["pension", "social"]):
        department = "District Social Welfare Office"
    elif any(token in issue_l for token in ["student", "scholarship", "education"]):
        department = "District Education Office"
    elif any(token in issue_l for token in ["farmer", "agri", "crop"]):
        department = "District Agriculture Office"
    else:
        department = "Citizen Service Center"

    portal = STATE_PORTALS.get(state, "https://www.india.gov.in")
    return {
        "state": state,
        "district": district,
        "department": department,
        "contact": f"Use {portal} and district helpdesk for {district}, {state}.",
        "portal": portal,
    }
