#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database.models import Lead
from app.database.session import async_session, init_db
from app.agents.permit_monitor import run_permit_monitor
from app.scoring.engine import calculate_score


async def seed():
    await init_db()

    leads_data = await run_permit_monitor()

    print(f"Found {len(leads_data)} potential leads from LADBS")

    high_value_count = 0
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
        if lead_data["is_high_value"]:
            high_value_count += 1

    async with async_session() as db:
        result = await db.execute(select(Lead.permit_number))
        existing = {row[0] for row in result if row[0]}

        new_count = 0
        for lead_data in leads_data:
            if lead_data["permit_number"] and lead_data["permit_number"] in existing:
                continue
            lead = Lead(**lead_data)
            db.add(lead)
            new_count += 1

        await db.commit()

        count_result = await db.execute(select(Lead).order_by(Lead.score.desc()))
        all_leads = count_result.scalars().all()

    print(f"\n{'='*65}")
    print(f"  Added {new_count} new leads | Total in DB: {len(all_leads)}")
    print(f"  High value leads: {high_value_count}")
    print(f"{'='*65}")

    if all_leads:
        print(f"\n{'Score':<7} {'Category':<25} {'Zip':<7} {'Company':<35}")
        print(f"{'-'*74}")
        for lead in sorted(all_leads, key=lambda l: l.score or 0, reverse=True)[:25]:
            name = (lead.company_name or "N/A")[:34]
            print(f"{lead.score:<7} {lead.service_category or 'N/A':<25} {lead.zip_code or 'N/A':<7} {name}")

    return all_leads


if __name__ == "__main__":
    asyncio.run(seed())
