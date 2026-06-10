import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database.session import async_session, init_db
from app.database.models import Lead
from app.agents.maps_scraper import scrape_google_maps
from app.agents.email_finder import enrich_lead_with_email
from app.scoring.engine import calculate_score


async def run_pipeline(enrich: bool = False):
    print("Initializing database...")
    await init_db()

    print("Scraping Google Maps...")
    raw = await scrape_google_maps()
    print(f"Scraped {len(raw)} leads")

    async with async_session() as db:
        result = await db.execute(select(Lead.company_name, Lead.address).where(Lead.source == "google_maps"))
        existing = set()
        for row in result:
            key = ((row[0] or "").lower().strip(), (row[1] or "").lower().strip())
            existing.add(key)

    saved = 0
    enriched = 0
    skipped = 0

    async with async_session() as db:
        for item in raw:
            dedup_key = (item["company_name"].lower().strip(), item.get("address", "").lower().strip())
            if dedup_key in existing:
                skipped += 1
                continue
            existing.add(dedup_key)

            try:
                if enrich:
                    item = await enrich_lead_with_email(item)
                    if item.get("email"):
                        enriched += 1

                score = calculate_score(
                    service_category=item.get("service_category", "general_electrical"),
                    urgency=item.get("urgency", "medium"),
                    zip_code=item.get("zip_code", ""),
                    estimated_cost=0,
                    permit_type="",
                    company_name=item.get("company_name", ""),
                    has_phone=bool(item.get("phone")),
                    has_website=bool(item.get("website")),
                )
                item["score"] = score
                item["is_high_value"] = score >= 50

                lead = Lead(
                    source=item["source"],
                    source_id=item["source_id"],
                    company_name=item["company_name"],
                    website=item["website"],
                    phone=item["phone"],
                    email=item.get("email"),
                    contact_name=item.get("contact_name"),
                    address=item["address"],
                    zip_code=item["zip_code"],
                    service_category=item["service_category"],
                    urgency=item["urgency"],
                    score=item["score"],
                    is_high_value=item["is_high_value"],
                    extra_data=item.get("extra_data"),
                )
                db.add(lead)
                saved += 1
            except Exception:
                pass

        await db.commit()

    print(f"\nSaved {saved} leads to database")
    print(f"Skipped {skipped} duplicates")
    if enrich:
        print(f"Enriched {enriched} with emails")
    print("Done!")


if __name__ == "__main__":
    enrich = "--enrich" in sys.argv
    asyncio.run(run_pipeline(enrich=enrich))
