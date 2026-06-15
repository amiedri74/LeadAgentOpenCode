from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from app.database.session import get_db
from app.database.models import Lead

router = APIRouter()


@router.get("")
async def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    source: Optional[str] = None,
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead)

    if source:
        query = query.where(Lead.source == source)
    if category:
        query = query.where(Lead.service_category == category)
    if min_score is not None:
        query = query.where(Lead.score >= min_score)

    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(desc(Lead.score)).offset(skip).limit(limit))
    leads = result.scalars().all()

    return {"total": total, "leads": [serialize_lead(l) for l in leads]}


@router.get("/stats")
async def lead_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Lead))
    high_value = await db.scalar(
        select(func.count()).select_from(Lead).where(Lead.is_high_value == True)
    )

    cats = await db.execute(
        select(Lead.service_category, func.count())
        .group_by(Lead.service_category)
    )

    return {
        "total_leads": total,
        "high_value_leads": high_value,
        "by_category": {row[0] or "unclassified": row[1] for row in cats},
    }


@router.get("/{lead_id}")
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    try:
        uid = UUID(lead_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid lead ID format")
    result = await db.execute(select(Lead).where(Lead.id == uid))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return serialize_lead(lead)


def serialize_lead(lead):
    source_url = None
    if lead.source == "google_maps" and lead.company_name:
        parts = [lead.company_name, lead.zip_code, "Los Angeles"]
        q = " ".join(p for p in parts if p)
        source_url = f"https://www.google.com/maps/search/{q.replace(' ', '+')}"
    elif lead.source == "ladbs_permit":
        source_url = "https://www.ladbs.org/permits"

    return {
        "id": str(lead.id),
        "source": lead.source,
        "source_url": source_url,
        "source_id": lead.source_id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "email": lead.email,
        "phone": lead.phone,
        "website": lead.website,
        "address": lead.address,
        "city": lead.city,
        "zip_code": lead.zip_code,
        "latitude": float(lead.latitude) if lead.latitude is not None else None,
        "longitude": float(lead.longitude) if lead.longitude is not None else None,
        "permit_number": lead.permit_number,
        "permit_type": lead.permit_type,
        "project_description": lead.project_description,
        "estimated_cost": float(lead.estimated_cost) if lead.estimated_cost else None,
        "service_category": lead.service_category,
        "urgency": lead.urgency,
        "score": lead.score,
        "is_high_value": lead.is_high_value,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
    }
