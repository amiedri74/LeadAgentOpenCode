import logging
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.database.models import OutreachDraft, Lead
from app.middleware import verify_api_key
from app.outreach.engine import send_email

router = APIRouter()
logger = logging.getLogger(__name__)


def _validate_uuid(value: str) -> UUID:
    """Validate and parse a UUID string."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")


async def _get_leads_map(db: AsyncSession, lead_ids: list[UUID]) -> dict[str, Lead]:
    """Fetch leads by IDs and return as a string-keyed dict."""
    if not lead_ids:
        return {}
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    return {str(l.id): l for l in result.scalars().all()}


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
async def list_drafts(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    query = select(OutreachDraft)
    if status:
        query = query.where(OutreachDraft.status == status)
    query = query.order_by(OutreachDraft.generated_at.desc())
    result = await db.execute(query)
    drafts = result.scalars().all()

    lead_ids = [d.lead_id for d in drafts]
    leads_map = await _get_leads_map(db, lead_ids)

    return {"drafts": [serialize_draft(d, leads_map.get(str(d.lead_id))) for d in drafts]}


@router.patch("/api/outreach/drafts/{draft_id}")
async def update_draft(
    draft_id: str,
    update: DraftUpdate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    uid = _validate_uuid(draft_id)

    result = await db.execute(select(OutreachDraft).where(OutreachDraft.id == uid))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if update.subject is not None:
        draft.subject = update.subject
    if update.body is not None:
        draft.body = update.body
    draft.status = "pending_review"

    leads_map = await _get_leads_map(db, [draft.lead_id])
    lead = leads_map.get(str(draft.lead_id))

    await db.commit()
    return {"ok": True, "draft": serialize_draft(draft, lead)}


@router.post("/api/outreach/drafts/{draft_id}/approve")
async def approve_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    uid = _validate_uuid(draft_id)

    result = await db.execute(select(OutreachDraft).where(OutreachDraft.id == uid))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = "approved"
    await db.commit()
    return {"ok": True}


@router.post("/api/outreach/send-batch")
async def send_batch(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
):
    result = await db.execute(
        select(OutreachDraft).where(OutreachDraft.status == "approved")
    )
    drafts = result.scalars().all()
    if not drafts:
        return {"sent": 0, "failed": 0, "message": "No approved drafts"}

    lead_ids = [d.lead_id for d in drafts]
    leads_map = await _get_leads_map(db, lead_ids)

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
                extra = lead.extra_data if isinstance(lead.extra_data, dict) else {}
                outreach = extra.get("outreach", {})
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
        except Exception:
            logger.exception(f"Failed to send draft {draft.id}")
            draft.status = "failed"
            failed += 1

    try:
        await db.commit()
    except Exception:
        logger.error("Failed to commit send_batch changes")
        return {"sent": sent, "failed": failed, "error": "Database commit failed"}

    return {"sent": sent, "failed": failed}
