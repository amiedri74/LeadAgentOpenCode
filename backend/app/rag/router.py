import asyncio
import logging
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import select
from app.database.session import get_db
from app.database.models import Lead
from app.rag import memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/index")
async def rebuild_index():
    async for db in get_db():
        result = await db.execute(select(Lead))
        leads = result.scalars().all()
        asyncio.create_task(memory.build_index_async(leads, force=True))
        return {"status": "started", "leads": len(leads)}
    return {"status": "error"}


@router.get("/status")
async def index_status():
    idx = memory.load_index()
    return {"indexed": len(idx["ids"]), "building": memory._building}


@router.get("/similar")
async def similar_leads(
    lead_id: str = Query(...),
    n: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.5, ge=0, le=1),
):
    try:
        UUID(lead_id)
    except ValueError:
        raise HTTPException(400, "Invalid lead ID")

    results = memory.find_similar_to_lead(lead_id, n=n, threshold=threshold)
    return {"similar": results}


@router.get("/search")
async def search_similar(
    q: str = Query(...),
    n: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.3, ge=0, le=1),
):
    results = memory.find_similar(q, n=n, threshold=threshold)
    return {"similar": results}
