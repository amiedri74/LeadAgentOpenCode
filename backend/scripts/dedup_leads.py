#!/usr/bin/env python3
"""
Find and report duplicate leads grouped by email or website.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, func
from app.database.session import async_session, init_db
from app.database.models import Lead


async def find_duplicates():
    await init_db()

    async with async_session() as db:
        for field, label in [("email", "Email"), ("website", "Website")]:
            col = getattr(Lead, field)
            result = await db.execute(
                select(col, func.count().label("cnt"), func.array_agg(Lead.id).label("ids"))
                .where(col.isnot(None)).where(col != "")
                .group_by(col)
                .having(func.count() > 1)
                .order_by(func.count().desc())
            )
            rows = result.all()

            if rows:
                print(f"\n=== Duplicate {label}s ({len(rows)} groups) ===")
                for val, cnt, ids in rows:
                    print(f"\n  {val} ({cnt} leads)")
                    r2 = await db.execute(
                        select(Lead).where(Lead.id.in_(ids)).order_by(Lead.score.desc())
                    )
                    for l in r2.scalars().all():
                        outcome = l.extra_data.get("outreach", {}).get("status", "-") if l.extra_data else "-"
                        print(f"    [{l.score:>3}] {l.company_name or '?'} | {l.phone or 'no phone'} | source={l.source} | outreach={outcome}")
            else:
                print(f"\n=== No duplicate {label}s found ===")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(find_duplicates())
