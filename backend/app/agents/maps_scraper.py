import re
from playwright.async_api import async_playwright, Page
from playwright_stealth import Stealth

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
            except Exception:
                pass

        try:
            await browser.close()
        except Exception:
            pass

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

    await page.wait_for_timeout(4000)

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
            await page.wait_for_timeout(1500)

            website = ""
            try:
                ws = page.locator('a[data-tooltip="Open website"]').first
                href = await ws.get_attribute("href", timeout=3000)
                if href and "maps.google" not in href and not href.startswith("javascript"):
                    website = href
            except Exception:
                pass

            leads.append({
                "source": "google_maps",
                "source_id": f"maps_{term.replace(' ', '_')}_{i}",
                "company_name": parsed["name"],
                "website": website,
                "phone": parsed["phone"],
                "address": parsed["address"],
                "zip_code": parsed["zip_code"],
                "service_category": "general_electrical",
                "urgency": "medium",
                "score": 40,
                "is_high_value": False,
            })
        except Exception:
            continue

    await page.close()
    await ctx.close()
    return leads
