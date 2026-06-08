import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def _parse_cost(val) -> float:
    if val is None:
        return 0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0


SUBTYPE_CATEGORY_MAP = {
    "Apartment": "commercial_electrical",
    "Commercial": "commercial_electrical",
    "1 or 2 Family Dwelling": "general_electrical",
}

CONTRACTOR_CATEGORY_KEYWORDS = [
    ("solar", "solar_electrical"),
    ("charger", "ev_charger"),
    ("chargie", "ev_charger"),
    ("tesla", "ev_charger"),
    ("generator", "generator"),
    ("lighting", "lighting"),
]


def classify_permit(p: dict) -> tuple:
    subtype = (p.get("permit_sub_type") or "").strip()
    contractor = (p.get("contractors_business_name") or "").lower()
    permit_type = p.get("permit_type", "")

    category = SUBTYPE_CATEGORY_MAP.get(subtype, "general_electrical")

    for kw, cat in CONTRACTOR_CATEGORY_KEYWORDS:
        if kw in contractor:
            category = cat
            break

    urgency = "medium"
    if "apartment" in subtype.lower() or "commercial" in subtype.lower():
        urgency = "high"

    return category, urgency


async def run_permit_monitor() -> list[dict]:
    leads = []
    all_zips = settings.tier1_zips + settings.tier2_zips
    zip_filter = '"' + '","'.join(all_zips) + '"'

    query_types = ["Electrical", "Bldg-Alter/Repair", "Bldg-Addition", "Bldg-New"]

    async with httpx.AsyncClient() as client:
        for ptype in query_types:
            try:
                resp = await client.get(
                    settings.permit_api_base,
                    params={
                        "$where": f"permit_type = '{ptype}' AND zip_code IN ({zip_filter})",
                        "$limit": 200,
                        "$order": "issue_date DESC",
                    },
                    timeout=30,
                )
                if resp.status_code != 200:
                    continue
                permits = resp.json()
            except Exception:
                continue

            for p in permits:
                zip_code = p.get("zip_code", "")
                permit_type = p.get("permit_type", "")
                contractor = p.get("contractors_business_name", "") or ""
                subtype = p.get("permit_sub_type", "") or ""

                if permit_type == "Electrical":
                    service_category, urgency = classify_permit(p)
                else:
                    contractor_lower = contractor.lower()
                    if not any(kw in contractor_lower for kw in [
                        "electric", "solar", "charger", "generator",
                        "lighting", "panel", "electrical",
                    ]):
                        continue
                    service_category, urgency = classify_permit(p)

                lead = {
                    "source": "ladbs_permit",
                    "source_id": p.get("pcis_permit", ""),
                    "company_name": contractor or subtype,
                    "address": f"{p.get('address_start', '')} {p.get('street_name', '')}".strip(),
                    "city": "Los Angeles",
                    "zip_code": zip_code,
                    "permit_number": p.get("pcis_permit", ""),
                    "permit_type": permit_type,
                    "permit_subtype": subtype,
                    "permit_status": p.get("status", ""),
                    "project_description": p.get("description", ""),
                    "estimated_cost": _parse_cost(p.get("estimated_cost")),
                    "service_category": service_category,
                    "urgency": urgency,
                    "score": 0,
                    "is_high_value": False,
                }
                leads.append(lead)

    return leads
