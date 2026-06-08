import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database.session import async_session, init_db
from app.database.models import Lead
from app.agents.contact_scraper import scrape_website
from app.utils.phone import normalize_phone


async def enrich_contacts():
    await init_db()

    async with async_session() as db:
        result = await db.execute(
            select(Lead).where(Lead.website.isnot(None))
            .where(Lead.website != "")
            .where(
                (Lead.email.is_(None)) | (Lead.email == "")
                | (Lead.phone.is_(None)) | (Lead.phone == "")
                | (Lead.contact_name.is_(None)) | (Lead.contact_name == "")
            )
        )
        leads = result.scalars().all()
        print(f"Found {len(leads)} leads to enrich")

    updated = 0
    failed = 0
    changed_leads = []

    for i, lead in enumerate(leads, 1):
        print(f"[{i}/{len(leads)}] {lead.company_name or lead.website}...", end=" ", flush=True)
        try:
            info = await scrape_website(lead.website)
            changed = False

            if info["primary_email"] and not lead.email:
                lead.email = info["primary_email"]
                changed = True
            if info["primary_phone"]:
                normalized = normalize_phone(info["primary_phone"])
                if normalized and not lead.phone:
                    lead.phone = normalized
                    changed = True
            if info["contact_name"] and not lead.contact_name:
                lead.contact_name = info["contact_name"]
                changed = True

            existing = lead.extra_data or {}
            if isinstance(existing, str):
                existing = {}
            existing["website_scrape"] = {
                "all_emails": info["emails"],
                "all_phones": info["phones"],
                "contact_name_found": info["contact_name"],
            }
            lead.extra_data = existing

            if changed:
                updated += 1
                changed_leads.append(lead)
                print("updated")
            else:
                print("no change")

        except Exception as e:
            print(f"error: {e}")
            failed += 1

    async with async_session() as db:
        for lead in changed_leads:
            db.add(lead)
        await db.commit()

    print(f"Updated: {updated}, Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(enrich_contacts())
