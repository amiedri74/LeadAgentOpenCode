import httpx
from urllib.parse import urlparse
from app.config import settings


async def find_emails_for_domain(domain: str) -> list[dict]:
    if not settings.hunter_api_key:
        return []

    domain = domain.lower().strip()
    if "://" in domain:
        domain = urlparse(domain).hostname or domain
    domain = domain.split("/")[0].split("?")[0].split("#")[0]
    if not domain or "." not in domain:
        return []

    url = "https://api.hunter.io/v2/domain-search"
    headers = {"X-API-Key": settings.hunter_api_key}
    params = {"domain": domain}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return []
            data = resp.json().get("data", {})
            emails = data.get("emails", [])
            return [
                {
                    "email": e["value"],
                    "first_name": e.get("first_name", ""),
                    "last_name": e.get("last_name", ""),
                    "position": e.get("position", ""),
                    "confidence": e.get("confidence", 0),
                    "type": e.get("type", ""),
                }
                for e in emails
            ]
        except Exception:
            return []


async def enrich_lead_with_email(lead: dict) -> dict:
    website = lead.get("website", "")
    if not website:
        return lead

    emails = await find_emails_for_domain(website)
    if emails:
        lead["email"] = emails[0]["email"]
        lead["contact_name"] = f"{emails[0].get('first_name', '')} {emails[0].get('last_name', '')}".strip()
        lead["extra_data"] = lead.get("extra_data") or {}
        lead["extra_data"]["hunter_emails"] = emails

    return lead
