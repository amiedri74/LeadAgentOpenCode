from fastapi import APIRouter
from app.agents.maps_scraper import scrape_google_maps

router = APIRouter()


@router.post("/maps")
async def trigger_maps_scrape():
    raw = await scrape_google_maps()
    return {"total": len(raw), "leads": raw}
