import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.database.models import OutreachDraft, Lead

router = APIRouter()
logger = logging.getLogger(__name__)


class DraftUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None


def serialize_draft(draft, lead=None):
    return {
        "id": str(draft.id),
        "lead_id": str(draft.lead_id),
        "status": draft.status,
        "subject": draft.subject,
        "body": draft.body,
        "generated_at": draft.generated_at.isoformat() if draft.generated_at else None,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else None,
        "company_name": lead.company_name if lead else None,
        "email": lead.email if lead else None,
        "phone": lead.phone if lead else None,
        "score": lead.score if lead else None,
        "service_category": lead.service_category if lead else None,
    }


@router.get("/api/outreach/drafts")
async def list_drafts(status: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(OutreachDraft)
    if status:
        query = query.where(OutreachDraft.status == status)
    query = query.order_by(OutreachDraft.generated_at.desc())
    result = await db.execute(query)
    drafts = result.scalars().all()

    lead_ids = [d.lead_id for d in drafts]
    leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads_map = {str(l.id): l for l in leads_result.scalars().all()}

    return {"drafts": [serialize_draft(d, leads_map.get(str(d.lead_id))) for d in drafts]}


@router.patch("/api/outreach/drafts/{draft_id}")
async def update_draft(draft_id: str, update: DraftUpdate, db: AsyncSession = Depends(get_db)):
    try:
        uid = UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid draft ID format")

    result = await db.execute(select(OutreachDraft).where(OutreachDraft.id == uid))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if update.subject is not None:
        draft.subject = update.subject
    if update.body is not None:
        draft.body = update.body
    draft.status = "pending_review"

    lead_result = await db.execute(select(Lead).where(Lead.id == draft.lead_id))
    lead = lead_result.scalar_one_or_none()

    await db.commit()
    return {"ok": True, "draft": serialize_draft(draft, lead)}


@router.post("/api/outreach/drafts/{draft_id}/approve")
async def approve_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = UUID(draft_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid draft ID format")

    result = await db.execute(select(OutreachDraft).where(OutreachDraft.id == uid))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = "approved"
    await db.commit()
    return {"ok": True}


@router.post("/api/outreach/send-batch")
async def send_batch(db: AsyncSession = Depends(get_db)):
    from app.outreach.engine import send_email

    result = await db.execute(
        select(OutreachDraft).where(OutreachDraft.status == "approved")
    )
    drafts = result.scalars().all()
    if not drafts:
        return {"sent": 0, "failed": 0, "message": "No approved drafts"}

    lead_ids = [d.lead_id for d in drafts]
    leads_result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads_map = {str(l.id): l for l in leads_result.scalars().all()}

    sent = 0
    failed = 0
    for draft in drafts:
        lead = leads_map.get(str(draft.lead_id))
        if not lead or not lead.email:
            draft.status = "failed"
            failed += 1
            continue

        try:
            ok = await send_email(lead.email, draft.subject, draft.body)
            if ok:
                draft.status = "sent"
                extra = lead.extra_data or {}
                if isinstance(extra, str):
                    extra = {}
                outreach = extra.get("outreach", {})
                from datetime import datetime, timezone
                outreach.update({
                    "status": "sent",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "subject": draft.subject,
                    "body_preview": (draft.body or "")[:200],
                    "draft_id": str(draft.id),
                })
                extra["outreach"] = outreach
                lead.extra_data = extra
                sent += 1
            else:
                draft.status = "failed"
                failed += 1
        except Exception as e:
            logger.exception(f"Failed to send draft {draft.id}")
            draft.status = "failed"
            failed += 1

    await db.commit()
    return {"sent": sent, "failed": failed}
