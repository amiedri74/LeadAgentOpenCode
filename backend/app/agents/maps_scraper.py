import re
import logging
from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth
from app.scoring.engine import calculate_score, detect_category_from_name

logger = logging.getLogger(__name__)

SEARCH_TERMS = [
    "property management Los Angeles",
    "ADU contractor Los Angeles",
    "solar installer Los Angeles",
    "HVAC contractor Los Angeles",
    "general contractor Los Angeles",
    "apartment management company Los Angeles",
    "electrician Los Angeles",
    "EV charger installer Los Angeles",
    "electrical contractor Los Angeles",
    "commercial electrician Los Angeles",
    "panel upgrade Los Angeles",
    "lighting contractor Los Angeles",
    "electrical contractor San Fernando Valley",
    "electrical contractor Santa Monica",
    "electrical contractor Glendale",
    "electrical contractor Burbank",
    "electrical contractor Pasadena",
    "electrical contractor Beverly Hills",
    "property management San Fernando Valley",
    "home renovation Los Angeles",
    "construction company Los Angeles",
    "remodeling contractor Los Angeles",
    "real estate property management Los Angeles",
    "facility management Los Angeles",
    "building maintenance Los Angeles",
    "handyman Los Angeles",
    "generator installer Los Angeles",
    "solar panel company Los Angeles",
    "battery storage installer Los Angeles",
    "electrical contractor Woodland Hills",
    "electrical contractor Sherman Oaks",
    "electrical contractor Encino",
    "electrical contractor Tarzana",
    "electrical contractor Calabasas",
    "property manager Santa Monica",
    "property manager Glendale",
    "property manager Pasadena",
    "property manager Burbank",
    "electrical contractor North Hollywood",
    "electrical contractor Van Nuys",
    "electrical contractor Reseda",
    "electrical contractor Chatsworth",
    "electrical contractor Northridge",
    "electrical contractor Canoga Park",
    "electrical contractor Winnetka",
    "electrical contractor Granada Hills",
    "electrical contractor Porter Ranch",
    "electrical contractor Studio City",
    "electrical contractor Valley Village",
    "electrical contractor Toluca Lake",
    "electrical contractor West Hills",
    "electrical contractor Agoura Hills",
    "electrical contractor Hidden Hills",
    "electrical contractor West Hollywood",
    "electrical contractor Culver City",
    "electrical contractor Marina del Rey",
    "electrical contractor Venice",
    "electrical contractor Playa Vista",
    "electrical contractor El Segundo",
    "electrical contractor Hawthorne",
    "data cabling contractor Los Angeles",
    "network cabling installer Los Angeles",
    "home automation Los Angeles",
    "security system installer Los Angeles",
    "fire alarm contractor Los Angeles",
    "backup generator Los Angeles",
    "UPS battery backup Los Angeles",
    "restaurant electrical contractor Los Angeles",
    "commercial electrical maintenance Los Angeles",
    "office electrical contractor Los Angeles",
    "retail electrical contractor Los Angeles",
    "warehouse electrical contractor Los Angeles",
    "new construction electrician Los Angeles",
    "tenant improvement electrician Los Angeles",
    "HOA property management Los Angeles",
    "commercial property management Los Angeles",
    "property manager Woodland Hills",
    "property manager Sherman Oaks",
    "property manager Encino",
    "property manager Calabasas",
    "property manager Beverly Hills",
    "property manager Los Feliz",
    "property manager Silver Lake",
    "property manager West Hollywood",
    "property manager Culver City",
    "general contractor Glendale",
    "general contractor Pasadena",
    "general contractor Santa Monica",
    "general contractor Beverly Hills",
    "remodeling contractor Glendale",
    "remodeling contractor Pasadena",
    "home renovation Santa Monica",
    "home renovation Beverly Hills",
    "home renovation Woodland Hills",
]


def extract_zip(text: str) -> str:
    m = re.search(r"\b(9\d{4})\b", text)
    return m.group(1) if m else ""


def extract_phone(text: str) -> str:
    m = re.search(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return m.group(0) if m else ""


def clean_name(name: str) -> str:
    name = re.sub(r"[^\x20-\x7E]", "", name)
    name = re.sub(r"^Sponsored\s*", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s*No reviews.*", "", name, flags=re.IGNORECASE).strip()
    if len(name) > 150:
        name = name[:150]
    return name


def clean_address(addr: str) -> str:
    addr = re.sub(r"[^\x20-\x7E]", "", addr)
    parts = [p.strip() for p in addr.split() if p.strip()]
    return " ".join(parts) if parts else ""


def parse_article_text(text: str) -> dict | None:
    if not text:
        return None
    text = text.replace("\u200f", "").replace("\u200e", "")
    phone = extract_phone(text)
    zip_code = extract_zip(text)
    rating_match = re.search(r"(\d+\.\d+)", text)
    rating = rating_match.group(1) if rating_match else ""

    if rating_match:
        name = re.split(r"\s{2,}\d+\.\d+", text)[0].strip()
    elif "No reviews" in text:
        name = text.split("No reviews")[0].strip()
    else:
        parts = text.split("\n")
        name = parts[0].strip() if parts else ""

    name = clean_name(name)
    if not name or len(name) > 255:
        return None

    address = ""
    parts = text.split("·")
    if len(parts) >= 2:
        after_rating = parts[1].strip()
        addr_parts = re.split(r"(?:Open|Closed)\s*[·]?\s*", after_rating)
        address = clean_address(addr_parts[0].strip())

    exclude_keywords = ["charging station", "electrify america"]
    name_lower = name.lower()
    if any(kw in name_lower for kw in exclude_keywords):
        return None

    return {"name": name, "phone": phone, "rating": rating, "address": address, "zip_code": zip_code}


async def scrape_google_maps() -> list[dict]:
    all_leads = []
    seen = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        stealth_obj = Stealth()

        for term in SEARCH_TERMS:
            try:
                leads = await _scrape_term(browser, stealth_obj, term, seen)
                all_leads.extend(leads)
            except Exception as e:
                logger.warning("Search term %r failed: %s", term, e)

        try:
            await browser.close()
        except Exception as e:
            logger.warning("browser.close() failed: %s", e)

    return all_leads


async def _scrape_term(browser, stealth_obj, term: str, seen: set) -> list[dict]:
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    page = await ctx.new_page()
    await stealth_obj.apply_stealth_async(page)

    leads = []
    search_url = f"https://www.google.com/maps/search/{term.replace(' ', '+')}"

    try:
        await page.goto(search_url, timeout=20000, wait_until="domcontentloaded")
    except Exception:
        await ctx.close()
        return leads

    await page.wait_for_timeout(2000)

    articles = page.locator("div[role=\"article\"]")
    try:
        count = await articles.count()
    except Exception:
        await ctx.close()
        return leads

    for i in range(min(count, 20)):
        try:
            art = articles.nth(i)
            text = await art.text_content() or ""
            parsed = parse_article_text(text)
            if not parsed or not parsed["name"] or parsed["name"] in seen:
                continue
            seen.add(parsed["name"])

            await art.click()
            await page.wait_for_timeout(800)

            website = ""
            try:
                ws = page.locator('a[data-tooltip="Open website"]').first
                href = await ws.get_attribute("href", timeout=2000)
                if href and "maps.google" not in href and not href.startswith("javascript"):
                    website = href
            except Exception as e:
                logger.debug("Website fetch failed for %s: %s", parsed.get("name", "?"), e)

            detected_cat = detect_category_from_name(parsed["name"]) or "general_electrical"

            score = calculate_score(
                service_category=detected_cat,
                urgency="medium",
                zip_code=parsed["zip_code"],
                estimated_cost=0,
                permit_type="",
                company_name=parsed["name"],
                has_phone=bool(parsed["phone"]),
                has_email=False,
                has_website=bool(website),
            )

            leads.append({
                "source": "google_maps",
                "source_id": f"maps_{term.replace(' ', '_')}_{i}",
                "company_name": parsed["name"],
                "website": website,
                "phone": parsed["phone"],
                "address": parsed["address"],
                "zip_code": parsed["zip_code"],
                "service_category": detected_cat,
                "urgency": "medium",
                "score": score,
                "is_high_value": score >= 50,
            })
        except Exception as e:
            logger.debug("Item %d scraping failed: %s", i, e)
            continue

    await page.close()
    await ctx.close()
    return leads
