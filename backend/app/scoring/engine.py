import re
from app.config import settings
from app.rag import memory


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

CATEGORY_KEYWORDS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bev\b|\belectric\s+vehicle\b|\bcharging\b|\bcharger\b|\bchargepoint\b", re.I), "ev_charger"),
    (re.compile(r"\bsolar\b|\bphotovoltaic\b|\bpv\b|\bsun\s?power\b", re.I), "solar_electrical"),
    (re.compile(r"\bcommercial\s+electric\b|\bindustrial\s+electric\b|\brestaurant\b|\boffice\b|\bretail\b|\bwarehouse\b", re.I), "commercial_electrical"),
    (re.compile(r"\bgenerator\b|\bbackup\s+power\b|\bbattery\s+storage\b|\bstandby\b", re.I), "generator"),
    (re.compile(r"\bpanel\s+upgrade\b|\bbreaker\b|\belectrical\s+panel\b|\bmain\s+panel\b", re.I), "panel_upgrade"),
    (re.compile(r"\badu\b|\baccessory\s+dwelling\b|\bgranny\s+flat\b|\bguest\s+house\b", re.I), "adu_electrical"),
    (re.compile(r"\blighting\b|\bchandelier\b|\brecessed\b|\blandscape\s+lighting\b|\boutdoor\s+lighting\b", re.I), "lighting"),
    (re.compile(r"\brewire\b|\bwiring\b|\bremodel\b|\brenovation\b", re.I), "rewiring"),
    (re.compile(r"\bdata\b|\bnetwork\b|\bcabling\b|\bfiber\b|\bstructured\s+cabling\b|\bcat6\b", re.I), "commercial_electrical"),
]


def detect_category_from_name(company_name: str) -> str | None:
    if not company_name:
        return None
    for pattern, category in CATEGORY_KEYWORDS:
        if pattern.search(company_name):
            return category
    return None


def calculate_score(
    service_category: str,
    urgency: str,
    zip_code: str,
    estimated_cost: float,
    permit_type: str,
    company_name: str = "",
    has_phone: bool = False,
    has_email: bool = False,
    has_website: bool = False,
) -> int:
    score = 0

    detected = detect_category_from_name(company_name)
    effective_category = detected or service_category
    category_score = CATEGORY_SCORES.get(effective_category, 5)
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

    if has_phone:
        score += 5
    if has_email:
        score += 5
    if has_website:
        score += 3

    return min(score, 100)


def rag_boost(lead_text: str, current_score: int) -> int:
    similar = memory.find_similar(lead_text, n=3, threshold=0.4)
    if not similar:
        return current_score

    avg_sim = sum(s["similarity"] for s in similar) / len(similar)
    if avg_sim > 0.7:
        return min(current_score + 10, 100)
    elif avg_sim > 0.55:
        return min(current_score + 5, 100)
    return current_score
