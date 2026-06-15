"""Enrich high-value leads with emails from their websites."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database.session import async_session, init_db
from app.database.models import Lead
from app.agents.contact_scraper import scrape_website


async def enrich_hv_leads():
    await init_db()

    async with async_session() as db:
        result = await db.execute(
            select(Lead)
            .where(Lead.score >= 50)
            .where((Lead.email.is_(None)) | (Lead.email == "") | (Lead.email.notlike("%@%")))
            .where(Lead.website.isnot(None))
            .where(Lead.website != "")
            .order_by(Lead.score.desc())
            .limit(50)
        )
        leads = result.scalars().all()

    if not leads:
        print("No HV leads need enrichment")
        return

    print(f"Enriching {len(leads)} high-value leads...")
    updated = 0
    changed_leads = []

    for i, lead in enumerate(leads, 1):
        print(f"[{i}/{len(leads)}] {lead.company_name or lead.website}...", end=" ", flush=True)
        try:
            info = await scrape_website(lead.website)
            if info["primary_email"]:
                lead.email = info["primary_email"]
                updated += 1
                changed_leads.append(lead)
                print(f"email: {info['primary_email']}")
            else:
                print("no email found")
        except Exception as e:
            print(f"error: {e}")

    async with async_session() as db:
        for lead in changed_leads:
            db.add(lead)
        await db.commit()

    print(f"\nUpdated {updated} leads with new emails")


if __name__ == "__main__":
    asyncio.run(enrich_hv_leads())
