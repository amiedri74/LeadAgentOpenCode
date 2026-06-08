#!/usr/bin/env python3
"""
Daily Automation Workflow for Amy Electric Lead Agent
Runs: scrape permits, enrich leads, score, send alerts
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database.models import Lead
from app.database.session import async_session, init_db
from app.agents.permit_monitor import run_permit_monitor
from app.scoring.engine import calculate_score


async def daily_workflow(include_maps: bool = False):
    print("=" * 60)
    print("Amy Electric Lead Agent — Daily Workflow")
    print("=" * 60)

    await init_db()

    print("\n[1/4] Scraping LADBS permits...")
    leads_data = await run_permit_monitor()
    print(f"  Found {len(leads_data)} potential leads")

    print("\n[2/4] Scoring and storing permit leads...")
    for lead_data in leads_data:
        score = calculate_score(
            service_category=lead_data.get("service_category", "general_electrical"),
            urgency=lead_data.get("urgency", "medium"),
            zip_code=lead_data.get("zip_code", ""),
            estimated_cost=float(lead_data.get("estimated_cost", 0) or 0),
            permit_type=lead_data.get("permit_type", ""),
        )
        lead_data["score"] = score
        lead_data["is_high_value"] = score >= 50

    async with async_session() as db:
        result = await db.execute(select(Lead.permit_number))
        existing = {row[0] for row in result if row[0]}

        new_count = 0
        for lead_data in leads_data:
            if lead_data["permit_number"] and lead_data["permit_number"] in existing:
                continue
            db.add(Lead(**lead_data))
            new_count += 1

        if include_maps:
            print("\n[3/4] Scraping Google Maps...")
            from app.agents.maps_scraper import scrape_google_maps
            maps_leads = await scrape_google_maps()
            print(f"  Scraped {len(maps_leads)} leads")

            existing_names = set()
            maps_result = await db.execute(select(Lead.company_name, Lead.address).where(Lead.source == "google_maps"))
            for row in maps_result:
                key = ((row[0] or "").lower().strip(), (row[1] or "").lower().strip())
                existing_names.add(key)

            maps_new = 0
            for item in maps_leads:
                dedup_key = (item["company_name"].lower().strip(), item.get("address", "").lower().strip())
                if dedup_key in existing_names:
                    continue
                existing_names.add(dedup_key)
                score = calculate_score(
                    service_category=item.get("service_category", "general_electrical"),
                    urgency=item.get("urgency", "medium"),
                    zip_code=item.get("zip_code", ""),
                    estimated_cost=0,
                    permit_type="",
                )
                item["score"] = score
                item["is_high_value"] = score >= 50
                db.add(Lead(
                    source=item["source"],
                    source_id=item["source_id"],
                    company_name=item["company_name"],
                    website=item["website"],
                    phone=item["phone"],
                    address=item["address"],
                    zip_code=item["zip_code"],
                    service_category=item["service_category"],
                    urgency=item["urgency"],
                    score=item["score"],
                    is_high_value=item["is_high_value"],
                ))
                maps_new += 1
            print(f"  {maps_new} new maps leads added")

        await db.commit()

        result = await db.execute(select(Lead).order_by(Lead.score.desc()))
        all_leads = result.scalars().all()

    high_value = [l for l in all_leads if l.is_high_value]

    print(f"  {new_count} new leads added")
    print(f"  Total leads: {len(all_leads)}")
    print(f"  High-value leads: {len(high_value)}")

    step = "3/4" if include_maps else "3/3"
    print(f"\n[{step}] Whale alerts — Top 5 high-value leads:")
    print(f"  {'Score':<7} {'Company':<35} {'Category':<22} {'Zip':<7}")
    print(f"  {'-'*71}")
    for lead in high_value[:5]:
        print(f"  {lead.score:<7} {(lead.company_name or 'N/A'):<35} {(lead.service_category or 'N/A'):<22} {lead.zip_code or 'N/A':<7}")

    print("\n" + "=" * 60)
    print("Workflow complete.")
    print("=" * 60)

    return len(leads_data)


if __name__ == "__main__":
    include_maps = "--maps" in sys.argv
    asyncio.run(daily_workflow(include_maps=include_maps))
