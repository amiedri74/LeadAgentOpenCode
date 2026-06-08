import logging
import re
import httpx
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
CONTACT_KEYWORDS = ["contact", "about", "team", "support", "help", "get-in-touch", "contact-us", "about-us"]

_KNOWN_BAD_EMAIL_PATTERNS = re.compile(
    r"^[%@\s]|%[0-9a-fA-F]{2}|\.(png|jpg|gif|svg|jpeg)$|"
    r"(Call|Fax|Phone|Tel|Email|Web|Home|Team|Info)$|"
    r"^(contact|hello|support|admin|sales|team|noreply|no-reply|info)@\w*\.\w+$"
)

_EMAIL_USERNAME_BLACKLIST = {"contact", "hello", "support", "admin", "sales", "team", "noreply", "no-reply", "info", "mail", "inquiries"}


async def scrape_website(url: str) -> dict:
    if not url:
        return {"emails": [], "phones": [], "contact_name": ""}

    domain = urlparse(url).hostname or ""
    found_emails = set()
    found_phones = set()

    pages_to_check = [url]
    checked = set()

    async with httpx.AsyncClient(
        timeout=10,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    ) as client:
        for page_url in pages_to_check:
            if page_url in checked or len(checked) >= 3:
                break
            checked.add(page_url)

            try:
                resp = await client.get(page_url)
                if resp.status_code != 200:
                    logger.debug("HTTP %d for %s", resp.status_code, page_url)
                    continue
                html = resp.text
            except Exception as exc:
                logger.debug("Failed to fetch %s: %s", page_url, exc)
                continue

            soup = BeautifulSoup(html, "html.parser")

            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text().strip().lower()

                if href.startswith("mailto:"):
                    found_emails.add(href[7:].split("?")[0])

                if href.startswith("tel:"):
                    found_phones.add(href[4:].split("?")[0].strip())

                full = urljoin(page_url, href)
                if any(kw in href.lower() or kw in text for kw in CONTACT_KEYWORDS):
                    parsed = urlparse(full)
                    if parsed.hostname == domain and full not in checked and len(pages_to_check) < 3:
                        pages_to_check.append(full)

            body = soup.get_text()
            for match in EMAIL_RE.findall(body):
                found_emails.add(match)
            for match in PHONE_RE.findall(body):
                found_phones.add(match)

    valid = [e for e in found_emails if not _KNOWN_BAD_EMAIL_PATTERNS.search(e)]
    email = next((e for e in valid if e.split("@")[0].lower() not in _EMAIL_USERNAME_BLACKLIST), "")
    if not email:
        email = next(iter(valid), "")
    phone = next((p for p in found_phones), "")

    contact_name = ""
    if email:
        name_part = email.split("@")[0].replace(".", " ").replace("_", " ").replace("-", " ").title()
        if not any(word in name_part.lower() for word in ["info", "contact", "hello", "support", "admin", "sales", "team"]):
            contact_name = name_part

    return {
        "emails": list(found_emails),
        "phones": list(found_phones),
        "contact_name": contact_name,
        "primary_email": email,
        "primary_phone": phone,
    }


async def enrich_lead_from_website(lead: dict) -> dict:
    url = lead.get("website", "") or lead.get("url", "")
    if not url:
        return lead

    info = await scrape_website(url)

    if info["primary_email"] and not lead.get("email"):
        lead["email"] = info["primary_email"]
    if info["primary_phone"] and not lead.get("phone"):
        lead["phone"] = info["primary_phone"]
    if info["contact_name"] and not lead.get("contact_name"):
        lead["contact_name"] = info["contact_name"]

    existing = lead.get("extra_data") or {}
    if isinstance(existing, str):
        existing = {}
    existing["website_scrape"] = {
        "all_emails": info["emails"],
        "all_phones": info["phones"],
        "contact_name_found": info["contact_name"],
    }
    lead["extra_data"] = existing

    return lead
