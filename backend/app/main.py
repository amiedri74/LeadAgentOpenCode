from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.session import init_db, engine
from app.api import leads, dashboard, scrape, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except Exception as e:
        print(f"Database init failed: {e}")
        raise
    yield
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(scrape.router, prefix="/api/scrape", tags=["scrape"])
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(ws.router, prefix="", tags=["websocket"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
