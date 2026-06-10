#!/usr/bin/env python3
"""Re-score all leads using the improved scoring engine with name detection + contact boosts."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database.session import async_session
from app.database.models import Lead
from app.scoring.engine import calculate_score


async def rescore():
    async with async_session() as db:
        result = await db.execute(select(Lead))
        leads = result.scalars().all()
        print(f"Re-scoring {len(leads)} leads...")

        updated = 0
        for lead in leads:
            new_score = calculate_score(
                service_category=lead.service_category or "general_electrical",
                urgency=lead.urgency or "medium",
                zip_code=lead.zip_code or "",
                estimated_cost=float(lead.estimated_cost) if lead.estimated_cost else 0,
                permit_type=lead.permit_type or "",
                company_name=lead.company_name or "",
                has_phone=bool(lead.phone),
                has_email=bool(lead.email and "@" in lead.email),
                has_website=bool(lead.website and lead.website.startswith("http")),
            )

            if new_score != lead.score:
                lead.score = new_score
                lead.is_high_value = new_score >= 50
                updated += 1

        await db.commit()
        print(f"Updated: {updated} leads re-scored")

        high = sum(1 for l in leads if l.score >= 50)
        print(f"High-value (>=50): {high}")
        print(f"Total leads: {len(leads)}")


asyncio.run(rescore())
