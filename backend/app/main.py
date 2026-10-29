from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.agent.bot import run_call

app = FastAPI(title="J's Cleaners AI Receptionist")


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.websocket("/ws/call")
async def call(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Call started")
    try:
        await run_call(websocket)
    except ValueError as e:  # origin rejected by the transport
        logger.warning(str(e))
        await websocket.close(code=4003)


# In production the built React app is copied here and served from the same origin.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
