from app.config import settings


CATEGORY_SCORES = {
    "ev_charger": 30,
    "panel_upgrade": 25,
    "commercial_electrical": 20,
    "adu_electrical": 20,
    "generator": 18,
    "solar_electrical": 15,
    "rewiring": 15,
    "lighting": 10,
    "general_electrical": 8,
}

URGENCY_SCORES = {
    "high": 25,
    "medium": 10,
    "low": 0,
}


def calculate_score(
    service_category: str,
    urgency: str,
    zip_code: str,
    estimated_cost: float,
    permit_type: str,
) -> int:
    score = 0

    category_score = CATEGORY_SCORES.get(service_category, 5)
    score += category_score

    urgency_score = URGENCY_SCORES.get(urgency, 5)
    score += urgency_score

    if zip_code in settings.tier1_zips:
        score += 15
    elif zip_code in settings.tier2_zips:
        score += 10

    if estimated_cost and estimated_cost > 50000:
        score += 10
    elif estimated_cost and estimated_cost > 25000:
        score += 5
    elif estimated_cost and estimated_cost > 10000:
        score += 3

    if permit_type and permit_type.lower() == "electrical":
        score += 15

    return min(score, 100)
