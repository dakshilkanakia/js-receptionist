from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_owner
from app.db.models import CallbackRequest

router = APIRouter(prefix="/api/callbacks", tags=["callbacks"], dependencies=[Depends(require_owner)])


class CallbackOut(BaseModel):
    id: int
    call_id: int | None
    first_name: str
    phone_e164: str
    reason: str
    status: str
    owner_note: str | None
    created_at: datetime
    handled_at: datetime | None


class CallbackPatch(BaseModel):
    status: Literal["pending", "done"] | None = None
    owner_note: str | None = Field(default=None, max_length=2000)


@router.get("", response_model=list[CallbackOut])
async def list_callbacks(status: Literal["pending", "done", "all"] = "pending", db: AsyncSession = Depends(get_db)):
    q = select(CallbackRequest)
    if status != "all":
        q = q.where(CallbackRequest.status == status)
    order = CallbackRequest.created_at.asc() if status == "pending" else CallbackRequest.created_at.desc()
    return (await db.scalars(q.order_by(order).limit(500))).all()


@router.patch("/{callback_id}", response_model=CallbackOut)
async def update_callback(callback_id: int, body: CallbackPatch, db: AsyncSession = Depends(get_db)):
    cb = await db.get(CallbackRequest, callback_id)
    if cb is None:
        raise HTTPException(404, "Callback not found")
    if body.status is not None and body.status != cb.status:
        cb.status = body.status
        cb.handled_at = datetime.now(timezone.utc) if body.status == "done" else None
    if body.owner_note is not None:
        cb.owner_note = body.owner_note.strip() or None
    await db.commit()
    return cb
