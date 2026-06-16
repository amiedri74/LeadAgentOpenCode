from fastapi import APIRouter, Depends
from app.agents.maps_scraper import scrape_google_maps
from app.middleware import verify_api_key

router = APIRouter()


@router.post("/maps")
async def trigger_maps_scrape(_api_key: str = Depends(verify_api_key)):
    raw = await scrape_google_maps()
    return {"total": len(raw), "leads": raw}
