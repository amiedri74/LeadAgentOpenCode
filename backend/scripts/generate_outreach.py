"""Generate 10 outreach drafts for the highest-value uncontacted leads."""
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import async_session, init_db
from app.database.models import Lead, OutreachDraft
from app.outreach.engine import generate_email
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DAILY_LIMIT = 10


async def main():
    await init_db()

    async with async_session() as db:
        contacted_ids = db.execute(
            select(OutreachDraft.lead_id)
        )
        contacted = {str(row[0]) for row in (await contacted_ids).all()}

        result = await db.execute(
            select(Lead)
            .where(Lead.email.isnot(None))
            .where(Lead.email != "")
            .where(Lead.score >= 40)
            .order_by(Lead.score.desc())
            .limit(100)
        )
        candidates = [l for l in result.scalars().all() if str(l.id) not in contacted]

        if not candidates:
            logger.info("No new leads to generate drafts for")
            return

        to_process = candidates[:DAILY_LIMIT]
        logger.info(f"Generating drafts for {len(to_process)} leads")

        created = 0
        for lead in to_process:
            try:
                subject, body = await generate_email(lead)
                draft = OutreachDraft(
                    lead_id=lead.id,
                    status="pending_review",
                    subject=subject,
                    body=body,
                )
                db.add(draft)
                created += 1
                logger.info(f"[{created}/{len(to_process)}] Draft for {lead.company_name}")
            except Exception as e:
                logger.error(f"Failed for {lead.company_name}: {e}")

        await db.commit()
        logger.info(f"Created {created} drafts")


if __name__ == "__main__":
    asyncio.run(main())
