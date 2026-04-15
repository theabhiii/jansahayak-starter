from __future__ import annotations


def check_eligibility(query: str, state: str) -> dict:
    return {
        "eligible": "likely",
        "reason": f"Eligibility appears likely based on the question context and location in {state}. Final confirmation needs official criteria and applicant details.",
    }



def application_status(reference_id: str | None = None) -> dict:
    return {
        "status": "mocked",
        "message": "This is a demo status endpoint. In production, this would call a live application-status system.",
    }



def route_grievance(issue: str, state: str, district: str) -> dict:
    department = "District Food and Civil Supplies Office" if "ration" in issue.lower() else "Citizen Service Center"
    return {
        "state": state,
        "district": district,
        "department": department,
        "contact": f"Visit the {district} office portal or nearest help center.",
    }
