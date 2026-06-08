import httpx
import json
from typing import Optional
from app.config import settings


SERVICE_KEYWORDS = {
    "ev_charger": ["ev", "electric vehicle", "charging station", "charger", "evse", "car charger"],
    "panel_upgrade": ["panel upgrade", "service upgrade", "electrical panel", "breaker", "subpanel", "200 amp"],
    "solar_electrical": ["solar", "photovoltaic", "pv", "solar panel", "solar system"],
    "adu_electrical": ["adu", "accessory dwelling", "granny flat", "guest house", "back house"],
    "lighting": ["lighting", "light fixture", "outdoor lighting", "landscape lighting"],
    "rewiring": ["rewire", "rewiring", "electrical rough", "knob and tube", "old wiring"],
    "commercial_electrical": ["commercial", "retail", "office", "restaurant", "warehouse"],
    "generator": ["generator", "backup power", "standby generator"],
}

URGENCY_KEYWORDS = {
    "high": ["emergency", "urgent", "immediate", "unsafe", "hazard", "outage", "no power"],
    "medium": ["scheduled", "planned", "upgrade", "renovation"],
}


def classify_with_keywords(description: str, permit_type: str) -> tuple[Optional[str], Optional[str], int]:
    if not description:
        description = ""
    desc_lower = description.lower()

    service_category = None
    urgency = "medium"
    base_score = 0

    if permit_type and "electrical" in permit_type.lower():
        base_score += 40

    for category, keywords in SERVICE_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                service_category = category
                break
        if service_category:
            break

    for urgency_level, keywords in URGENCY_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_lower:
                urgency = urgency_level
                break
        else:
            continue
        break

    return service_category, urgency, base_score


async def classify_with_ollama(description: str, permit_type: str) -> tuple[str, str, str]:
    system_prompt = """You are a lead classification AI for an electrical company. Given a building permit description,
classify it into exactly one service category and assign urgency and a brief rationale.

Return ONLY valid JSON: {"category": "...", "urgency": "high|medium|low", "rationale": "..."}

Categories: ev_charger, panel_upgrade, solar_electrical, adu_electrical, lighting, rewiring, commercial_electrical, generator, general_electrical, not_relevant
"""
    user_prompt = f"Permit type: {permit_type}\nDescription: {description}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.ollama_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "{}")
                result = json.loads(content)
                return (
                    result.get("category", "general_electrical"),
                    result.get("urgency", "medium"),
                    result.get("rationale", ""),
                )
    except Exception as e:
        pass

    cat, urg, _ = classify_with_keywords(description, permit_type)
    return cat or "general_electrical", urg, "keyword_fallback"
