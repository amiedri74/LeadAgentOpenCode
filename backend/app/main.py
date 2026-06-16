import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.session import init_db, engine, async_session
from app.database.models import Lead
from app.api import leads, dashboard, scrape, ws, contacts, outreach
from app.rag import router as rag_router
from app.rag import memory
from app.middleware.rate_limit import RateLimiter
from sqlalchemy import select

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        logger.error("Database init failed: %s", e)
        raise

    try:
        async with async_session() as db:
            result = await db.execute(select(Lead).limit(1))
            has_leads = result.first() is not None
        if has_leads:
            async with async_session() as db:
                result = await db.execute(select(Lead))
                leads_list = result.scalars().all()
            asyncio.create_task(memory.build_index_async(leads_list))
    except Exception as e:
        logger.warning("RAG index build deferred: %s", e)

    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Add rate limiting middleware (100 requests per minute per IP)
app.add_middleware(RateLimiter, calls=100, period=60)

# CORS - only allow configured origins (never allow all with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(scrape.router, prefix="/api/scrape", tags=["scrape"])
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(ws.router, prefix="", tags=["websocket"])
app.include_router(contacts.router, prefix="", tags=["contacts"])
app.include_router(outreach.router, prefix="", tags=["outreach"])
app.include_router(rag_router.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
