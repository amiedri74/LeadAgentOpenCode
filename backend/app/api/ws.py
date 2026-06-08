import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from app.database.session import async_session
from app.database.models import Lead

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def fetch_stats():
    async with async_session() as db:
        total = await db.scalar(select(func.count()).select_from(Lead))
        high = await db.scalar(select(func.count()).select_from(Lead).where(Lead.is_high_value == True))
        cats = await db.execute(select(Lead.service_category, func.count()).group_by(Lead.service_category))
        return {
            "total_leads": total,
            "high_value_leads": high,
            "by_category": {r[0] or "unclassified": r[1] for r in cats},
        }


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        stats = await fetch_stats()
        await ws.send_json({"type": "stats", "payload": stats})

        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                stats = await fetch_stats()
                await ws.send_json({"type": "stats", "payload": stats})
                continue

            if data:
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
