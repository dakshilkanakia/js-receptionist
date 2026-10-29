import hmac
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.deps import require_owner
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Simple brute-force protection: 10 failed logins per IP per 15 minutes.
_FAIL_WINDOW = 15 * 60
_MAX_FAILS = 10
_fails: dict[str, list[float]] = defaultdict(list)


class LoginIn(BaseModel):
    email: str
    password: str


def _client_ip(request: Request) -> str:
    return request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )


@router.post("/login")
async def login(body: LoginIn, request: Request) -> dict:
    ip = _client_ip(request)
    now = time.time()
    _fails[ip] = [t for t in _fails[ip] if now - t < _FAIL_WINDOW]
    if len(_fails[ip]) >= _MAX_FAILS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Try again later.")

    ok = bool(settings.owner_password) and hmac.compare_digest(
        body.email.strip().lower().encode(), settings.owner_email.lower().encode()
    ) & hmac.compare_digest(body.password.encode(), settings.owner_password.encode())
    if not ok:
        _fails[ip].append(now)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")

    request.session.clear()
    request.session["owner"] = settings.owner_email
    return {"email": settings.owner_email}


@router.post("/logout")
async def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
async def me(email: str = Depends(require_owner)) -> dict:
    return {"email": email}
