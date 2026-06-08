#!/usr/bin/env python3
"""
Find and optionally merge duplicate leads grouped by email or website.
--merge: auto-merge duplicates (keep best lead, merge missing fields)
--report: just report (default)
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from uuid import UUID
from sqlalchemy import select, func
from app.database.session import async_session, init_db
from app.database.models import Lead


MERGE_FIELDS = [
    ("phone", lambda a, b: bool(b) and not a),
    ("email", lambda a, b: bool(b) and not a),
    ("contact_name", lambda a, b: bool(b) and not a),
    ("website", lambda a, b: bool(b) and not a),
    ("address", lambda a, b: bool(b) and not a),
    ("city", lambda a, b: bool(b) and not a),
    ("zip_code", lambda a, b: bool(b) and not a),
]


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


async def merge_duplicates():
    await init_db()

    async with async_session() as db:
        for field in ["email", "website"]:
            col = getattr(Lead, field)
            result = await db.execute(
                select(col, func.count().label("cnt"), func.array_agg(Lead.id).label("ids"))
                .where(col.isnot(None)).where(col != "")
                .group_by(col)
                .having(func.count() > 1)
                .order_by(func.count().desc())
            )
            rows = result.all()

            for val, cnt, ids in rows:
                r2 = await db.execute(
                    select(Lead).where(Lead.id.in_(ids)).order_by(Lead.score.desc())
                )
                dupes = r2.scalars().all()
                if len(dupes) < 2:
                    continue

                best = dupes[0]
                rest = dupes[1:]
                changed = False

                for field_name, merge_fn in MERGE_FIELDS:
                    best_val = getattr(best, field_name)
                    for other in rest:
                        other_val = getattr(other, field_name)
                        if merge_fn(best_val, other_val):
                            setattr(best, field_name, other_val)
                            best_val = other_val
                            changed = True

                extra = best.extra_data or {}
                if isinstance(extra, str):
                    extra = {}
                merged_from = extra.get("merged_from", [])
                for other in rest:
                    merged_from.append({
                        "id": str(other.id),
                        "company_name": other.company_name,
                        "score": other.score,
                        "source": other.source,
                    })
                    await db.delete(other)
                if merged_from:
                    extra["merged_from"] = merged_from
                    best.extra_data = extra
                    changed = True

                if changed:
                    db.add(best)
                    print(f"  Merged {len(rest)} duplicates into {best.company_name} ({field}={val})")

        await db.commit()

    print("\nMerge complete.")


if __name__ == "__main__":
    do_merge = "--merge" in sys.argv
    if do_merge:
        asyncio.run(merge_duplicates())
    else:
        asyncio.run(find_duplicates())
