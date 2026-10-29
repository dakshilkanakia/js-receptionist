import hashlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.agent.bot import run_call
from app.config import settings
from app.db.models import Call
from app.db.session import SessionLocal
from app.facts.repo import latest_facts, seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as s:
        await seed_if_empty(s)
    yield


app = FastAPI(title="J's Cleaners AI Receptionist", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


def _ip_hash(websocket: WebSocket) -> str | None:
    ip = websocket.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        websocket.client.host if websocket.client else ""
    )
    if not ip:
        return None
    return hashlib.sha256(f"{settings.session_secret}:{ip}".encode()).hexdigest()[:32]


@app.websocket("/ws/call")
async def call(websocket: WebSocket) -> None:
    await websocket.accept()
    # Facts are read fresh for every call, so dashboard edits apply with no redeploy.
    async with SessionLocal() as s:
        facts_version_id, facts = await latest_facts(s)
        row = Call(facts_version_id=facts_version_id, ip_hash=_ip_hash(websocket))
        s.add(row)
        await s.commit()
        call_id = row.id
    logger.info(f"call {call_id} started (facts v{facts_version_id})")
    try:
        await run_call(websocket, call_id, facts)
    except ValueError as e:  # origin rejected by the transport
        logger.warning(str(e))
        await websocket.close(code=4003)


# In production the built React app is copied here and served from the same origin.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
