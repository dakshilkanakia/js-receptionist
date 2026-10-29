import hashlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.middleware.sessions import SessionMiddleware

from app.agent.bot import run_call
from app.api import auth, callbacks, calls, facts, stats, unanswered
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
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie="js_owner",
    max_age=7 * 24 * 3600,
    same_site="lax",
    https_only=settings.cookie_secure,
)
for module in (auth, calls, callbacks, unanswered, facts, stats):
    app.include_router(module.router)


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
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        # Client-side routes (e.g. /owner/calls) all load index.html.
        if path.startswith(("api/", "ws/")):
            raise HTTPException(404)
        file = STATIC_DIR / path
        if path and file.is_file() and STATIC_DIR in file.resolve().parents:
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
