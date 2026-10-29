from collections.abc import AsyncIterator

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def require_owner(request: Request) -> str:
    email = request.session.get("owner")
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return email
